"""Service for executing job runs asynchronously."""

import asyncio
import os
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.core.logging import get_logger
from app.domain.entities import (
    JobDefinition,
    JobRun,
    JobStatus,
    JobType,
)
from app.infrastructure.db.repositories import JobRepository, JobRunRepository
from app.infrastructure.query.engine import ExportQueryEngine
from app.infrastructure.queue.interface import MessageQueueInterface
from app.infrastructure.saas.client import SaaSApiClientInterface
from app.infrastructure.storage.file_generator import FileGenerator
from app.infrastructure.storage.interface import CloudStorageInterface

logger = get_logger(__name__)


class JobRunnerService:
    """Service for executing job runs in the background."""

    def __init__(
        self,
        job_repository: JobRepository,
        job_run_repository: JobRunRepository,
        query_engine: ExportQueryEngine,
        saas_client: SaaSApiClientInterface,
        cloud_storage: CloudStorageInterface | None = None,
        message_queue: MessageQueueInterface | None = None,
        max_workers: int = 5,
    ):
        """Initialize job runner."""
        self.job_repository = job_repository
        self.job_run_repository = job_run_repository
        self.query_engine = query_engine
        self.saas_client = saas_client
        self.cloud_storage = cloud_storage
        self.message_queue = message_queue
        self.max_workers = max_workers
        self.settings = get_settings()
        # Keep in-memory queue as fallback
        self._queue: asyncio.Queue = asyncio.Queue()
        self._workers: list[asyncio.Task] = []
        self._running = False

    async def start(self) -> None:
        """Start the job runner workers."""
        if self._running:
            return

        self._running = True
        self._workers = [
            asyncio.create_task(self._worker(f"worker-{i}")) for i in range(self.max_workers)
        ]
        logger.info(f"Started job runner with {self.max_workers} workers")

    async def stop(self) -> None:
        """Stop the job runner workers."""
        if not self._running:
            return

        self._running = False

        # Stop workers
        for worker in self._workers:
            worker.cancel()

        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers = []
        logger.info("Stopped job runner")

    async def queue_job_run(self, job: JobDefinition, job_run: JobRun) -> None:
        """Queue a job run for execution."""
        await self._queue.put((job, job_run))
        logger.debug(f"Queued job run {job_run.id} for job {job.id}")

    async def _worker(self, worker_id: str) -> None:
        """Worker coroutine that processes job runs."""
        logger.info(f"Worker {worker_id} started")
        while self._running:
            try:
                if self.message_queue:
                    # Poll external message queue (SQS, Azure Queue, GCP Pub/Sub)
                    messages = await self.message_queue.receive_messages(
                        max_messages=self.settings.message_queue_max_messages,
                        wait_time_seconds=self.settings.message_queue_wait_time,
                    )

                    for msg in messages:
                        try:
                            message_body = msg["body"]
                            receipt_handle = msg["receipt_handle"]

                            job_id = UUID(message_body["job_id"])
                            job_run_id = UUID(message_body["job_run_id"])

                            # Fetch job and job_run from database
                            job = await self.job_repository.get_by_id(job_id)
                            if not job:
                                logger.error(f"Job not found: {job_id}")
                                await self.message_queue.delete_message(receipt_handle)
                                continue

                            job_run = await self.job_run_repository.get_by_id(job_run_id)
                            if not job_run:
                                logger.error(f"Job run not found: {job_run_id}")
                                await self.message_queue.delete_message(receipt_handle)
                                continue

                            # Execute the job
                            await self._execute_job_run(job, job_run, worker_id)

                            # Delete message from queue after successful processing
                            await self.message_queue.delete_message(receipt_handle)

                        except Exception as e:
                            logger.error(
                                f"Worker {worker_id} error processing message: {e}", exc_info=True
                            )
                            # Message will become visible again after visibility timeout
                            # Don't delete it so it can be retried
                else:
                    # Fallback to in-memory queue
                    try:
                        job, job_run = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                        if job is not None and job_run is not None:
                            await self._execute_job_run(job, job_run, worker_id)
                    except TimeoutError:
                        continue

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}", exc_info=True)
                # Small delay before retrying to avoid tight loop on errors
                await asyncio.sleep(1)

        logger.info(f"Worker {worker_id} stopped")

    async def _execute_job_run(self, job: JobDefinition, job_run: JobRun, worker_id: str) -> None:
        """Execute a single job run."""
        logger.info(f"Worker {worker_id} executing job run {job_run.id} for job {job.name}")

        # Update status to running
        await self.job_run_repository.update_status(
            job_run.id,
            JobStatus.RUNNING,
            started_at=datetime.now(UTC),
        )

        try:
            if job.job_type == JobType.EXPORT:
                await self._execute_export_job(job, job_run, worker_id)
            elif job.job_type == JobType.IMPORT:
                await self._execute_import_job(job, job_run, worker_id)
            else:
                raise ValueError(f"Unknown job type: {job.job_type}")

            # Status is updated by _execute_export_job or _execute_import_job
            logger.info(f"Job run {job_run.id} completed successfully")

        except Exception as e:
            logger.error(f"Job run {job_run.id} failed: {e}", exc_info=True)
            # Update status to failed
            await self.job_run_repository.update_status(
                job_run.id,
                JobStatus.FAILED,
                completed_at=datetime.now(UTC),
                error_message=str(e),
            )

    async def _execute_export_job(
        self, job: JobDefinition, job_run: JobRun, worker_id: str
    ) -> None:
        """Execute an export job."""
        # Log job execution start
        logger.info(
            f"Job execution started: run_id={job_run.id}, job_id={job.id}, "
            f"job_type=export, entity={job.export_config.entity.value if job.export_config else 'unknown'}, "
            f"worker={worker_id}"
        )

        if not job.export_config:
            raise ValueError("Export job missing export_config")

        # Execute query using query engine (pass client_id for security)
        result = await self.query_engine.execute_export_query(
            job.export_config, client_id=job.client_id
        )

        records = result.get("records", [])
        count = result.get("count", len(records))
        # Get output field names for CSV/JSON headers (uses aliases if configured)
        output_fields = [f.output_name for f in job.export_config.fields]
        source_fields = job.export_config.get_source_fields()
        # Count how many fields have custom aliases
        aliased_fields = sum(1 for f in job.export_config.fields if f.as_ is not None)

        logger.info(
            f"Export query completed: run_id={job_run.id}, record_count={count}, "
            f"fields={len(output_fields)}, aliased_fields={aliased_fields}"
        )
        if aliased_fields > 0:
            logger.debug(
                f"Field mappings for run_id={job_run.id}: "
                f"source_fields={source_fields}, output_fields={output_fields}"
            )

        # Generate local file
        export_format = self.settings.export_file_format
        export_dir = self.settings.export_local_path

        # Ensure export directory exists
        os.makedirs(export_dir, exist_ok=True)

        if export_format == "csv":
            local_file_path = FileGenerator.generate_csv_file(records, output_fields, export_dir)
        elif export_format == "json":
            local_file_path = FileGenerator.generate_json_file(records, export_dir)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")

        # Upload to cloud storage if configured
        remote_file_path = None
        if self.cloud_storage:
            try:
                # Generate remote path: exports/{client_id}/{job_id}/{run_id}.{ext}
                file_ext = FileGenerator.get_file_extension(export_format)
                remote_file_path = f"exports/{job.client_id}/{job.id}/{job_run.id}{file_ext}"

                content_type = FileGenerator.get_content_type(export_format)
                await self.cloud_storage.upload_file(
                    local_file_path, remote_file_path, content_type=content_type
                )

                logger.info(
                    f"Export file uploaded to cloud storage: run_id={job_run.id}, "
                    f"remote_path={remote_file_path}"
                )
            except Exception as e:
                logger.error(f"Failed to upload file to cloud storage: {e}", exc_info=True)
                # Continue even if upload fails - file is still available locally
        else:
            logger.warning("Cloud storage not configured. File saved locally only.")

        # Clean up local file after upload (if successful)
        if self.cloud_storage and remote_file_path:
            try:
                os.remove(local_file_path)
                logger.debug(f"Removed local file: {local_file_path}")
            except Exception as e:
                logger.warning(f"Failed to remove local file: {e}")

        # Store file metadata in result_metadata
        result_metadata = {
            "count": count,
            "format": export_format,
            "fields": output_fields,
            "worker": worker_id,
        }
        if remote_file_path:
            result_metadata["remote_file_path"] = remote_file_path
        else:
            result_metadata["local_file_path"] = local_file_path

        # Update job run with result metadata (status already updated to SUCCEEDED)
        await self.job_run_repository.update_status(
            job_run.id,
            JobStatus.SUCCEEDED,
            completed_at=datetime.now(UTC),
            result_metadata=result_metadata,
        )

        # Log job execution completion
        logger.info(
            f"Job execution completed: run_id={job_run.id}, job_id={job.id}, "
            f"status=succeeded, record_count={count}, format={export_format}, "
            f"file_location={'cloud' if remote_file_path else 'local'}"
        )

    def _apply_field_mappings(
        self, record: dict[str, Any], field_mappings: dict[str, str]
    ) -> dict[str, Any]:
        """Apply field mappings to a record, renaming source columns to target fields.

        Args:
            record: Original record with source column names
            field_mappings: Dictionary mapping source column names to target field names

        Returns:
            New record with target field names
        """
        if not field_mappings:
            return record

        mapped_record: dict[str, Any] = {}
        for source_col, value in record.items():
            # If there's a mapping for this column, use the target name
            target_field = field_mappings.get(source_col, source_col)
            mapped_record[target_field] = value

        return mapped_record

    async def _execute_import_job(
        self, job: JobDefinition, job_run: JobRun, worker_id: str
    ) -> None:
        """Execute an import job with detailed error reporting."""
        # Log job execution start
        logger.info(
            f"Job execution started: run_id={job_run.id}, job_id={job.id}, "
            f"job_type=import, entity={job.import_config.entity.value if job.import_config else 'unknown'}, "
            f"worker={worker_id}"
        )

        if not job.import_config:
            raise ValueError("Import job missing import_config")

        # Get source file path from import config options
        source_file = job.import_config.options.get("source_file")

        if source_file:
            # Import from file (CSV or JSON)
            from app.infrastructure.storage.file_parser import FileParser

            logger.info(
                f"Import job processing file: run_id={job_run.id}, source_file={source_file}, "
                f"entity={job.import_config.entity.value}"
            )

            # Download file from cloud storage if needed
            local_file_path = source_file

            # If file is in cloud storage, download it first
            if self.cloud_storage and not os.path.exists(source_file):
                try:
                    # Download from cloud storage to temp location
                    from app.core.config import get_settings

                    settings = get_settings()
                    temp_dir = settings.export_local_path or "/tmp"
                    os.makedirs(temp_dir, exist_ok=True)
                    local_file_path = os.path.join(
                        temp_dir, f"import_{job_run.id}_{os.path.basename(source_file)}"
                    )

                    # Download file from cloud storage
                    logger.info(f"Downloading file from cloud storage: {source_file}")
                    await self.cloud_storage.download_file(source_file, local_file_path)
                    logger.info(f"Downloaded file to: {local_file_path}")
                except Exception as e:
                    error_msg = f"Failed to download file from cloud storage: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    await self.job_run_repository.update_status(
                        job_run.id,
                        JobStatus.FAILED,
                        completed_at=datetime.now(UTC),
                        error_message=error_msg,
                    )
                    return

            # Parse the file with row-level error tracking
            try:
                data = FileParser.parse_file(local_file_path)
            except Exception as e:
                error_msg = f"Failed to parse import file {source_file}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                await self.job_run_repository.update_status(
                    job_run.id,
                    JobStatus.FAILED,
                    completed_at=datetime.now(UTC),
                    error_message=error_msg,
                )
                return

            # Apply field mappings if configured
            field_mappings = job.import_config.get_field_mappings()
            if field_mappings:
                logger.info(
                    f"Applying field mappings for import: run_id={job_run.id}, "
                    f"mappings_count={len(field_mappings)}"
                )
                logger.debug(f"Field mappings: {field_mappings}")
                data = [self._apply_field_mappings(record, field_mappings) for record in data]

            # Import data with detailed error reporting (pass client_id for security)
            import_errors = []
            try:
                result = await self.saas_client.import_data(
                    job.import_config, client_id=job.client_id, data=data
                )

                # Check if import_data returned errors
                if isinstance(result, dict) and "errors" in result:
                    import_errors = result["errors"]
            except Exception as e:
                # Track import errors with row information
                error_msg = f"Import failed: {str(e)}"
                logger.error(error_msg, exc_info=True)

                # Try to provide row-level error information
                import_errors.append(
                    {
                        "row": None,
                        "message": error_msg,
                    }
                )

                await self.job_run_repository.update_status(
                    job_run.id,
                    JobStatus.FAILED,
                    completed_at=datetime.now(UTC),
                    error_message=error_msg,
                    result_metadata={
                        "import_errors": import_errors,
                        "failed_count": len(import_errors),
                    },
                )
                return

            # Store result metadata with error details
            result_metadata = {
                "imported_count": result.get("imported_count", 0),
                "updated_count": result.get("updated_count", 0),
                "deleted_count": result.get("deleted_count", 0),
                "skipped_count": result.get("skipped_count", 0),
                "failed_count": result.get("failed_count", 0),
                "worker": worker_id,
            }
            if source_file:
                result_metadata["source_file"] = source_file
            if import_errors:
                result_metadata["import_errors"] = import_errors

            # Update job run with result metadata
            await self.job_run_repository.update_status(
                job_run.id,
                JobStatus.SUCCEEDED if result.get("failed_count", 0) == 0 else JobStatus.FAILED,
                completed_at=datetime.now(UTC),
                result_metadata=result_metadata,
                error_message=f"{result.get('failed_count', 0)} records failed to import"
                if result.get("failed_count", 0) > 0
                else None,
            )

            # Log job execution completion
            logger.info(
                f"Job execution completed: run_id={job_run.id}, job_id={job.id}, "
                f"status={'succeeded' if result.get('failed_count', 0) == 0 else 'failed'}, "
                f"imported={result.get('imported_count', 0)}, updated={result.get('updated_count', 0)}, "
                f"deleted={result.get('deleted_count', 0)}, skipped={result.get('skipped_count', 0)}, "
                f"failed={result.get('failed_count', 0)}"
            )
        else:
            # Fallback: Fetch data from SaaS API (for backward compatibility)
            logger.warning("No source_file in import config. Fetching from SaaS API (mock).")
            data = await self.saas_client.fetch_data(
                job.import_config.entity, client_id=job.client_id, filters={}
            )

            # Import data using SaaS client (pass client_id for security)
            result = await self.saas_client.import_data(
                job.import_config, client_id=job.client_id, data=data
            )

            # Store result metadata
            result_metadata = {
                "imported_count": result.get("imported_count", 0),
                "updated_count": result.get("updated_count", 0),
                "failed_count": result.get("failed_count", 0),
                "worker": worker_id,
            }

            # Update job run with result metadata
            await self.job_run_repository.update_status(
                job_run.id,
                JobStatus.SUCCEEDED,
                completed_at=datetime.now(UTC),
                result_metadata=result_metadata,
            )

            # Log job execution completion
            logger.info(
                f"Job execution completed: run_id={job_run.id}, job_id={job.id}, "
                f"status=succeeded, imported={result.get('imported_count', 0)}, "
                f"updated={result.get('updated_count', 0)}, failed={result.get('failed_count', 0)}"
            )
