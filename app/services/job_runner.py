"""Service for executing job runs asynchronously."""

import asyncio
import json
import os
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.core.constants import STATS_UPDATE_INTERVAL
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
from app.infrastructure.storage.file_parser import FileParser
from app.infrastructure.storage.interface import CloudStorageInterface
from app.services.import_validator import ImportValidator

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

        # Get output field names for CSV/JSON headers (uses aliases if configured)
        output_fields = [f.output_name for f in job.export_config.fields]
        source_fields = job.export_config.get_source_fields()
        aliased_fields = sum(1 for f in job.export_config.fields if f.as_ is not None)

        # Generate local file
        export_format = self.settings.export_file_format
        export_dir = self.settings.export_local_path

        # Ensure export directory exists
        os.makedirs(export_dir, exist_ok=True)

        if export_format == "csv":
            # Use streaming export: SQL pushdown + batched CSV writes
            count, batch_gen = await self.query_engine.execute_export_streaming(
                job.export_config, client_id=job.client_id
            )

            # Wrap generator with progress tracking (time-throttled DB updates)
            rows_exported = 0
            batches_completed = 0
            last_stats_time = datetime.now(UTC)

            async def _tracked_batch_gen():
                nonlocal rows_exported, batches_completed, last_stats_time
                async for batch in batch_gen:
                    rows_exported += len(batch)
                    batches_completed += 1
                    is_first = batches_completed == 1
                    now = datetime.now(UTC)
                    elapsed = (now - last_stats_time).total_seconds()
                    if is_first or elapsed >= STATS_UPDATE_INTERVAL:
                        await self.job_run_repository.update_job_statistics(
                            job_run.id,
                            {
                                "rows_exported": rows_exported,
                                "total_rows": count,
                                "batches_completed": batches_completed,
                            },
                        )
                        last_stats_time = now
                    yield batch

            local_file_path, written = await FileGenerator.generate_csv_file_streaming(
                _tracked_batch_gen(), output_fields, export_dir
            )
            # Final stats update (last batch)
            await self.job_run_repository.update_job_statistics(
                job_run.id,
                {
                    "rows_exported": written,
                    "total_rows": count,
                    "batches_completed": batches_completed,
                },
            )
            # Use written count as authoritative
            count = written
        elif export_format == "json":
            # JSON export falls back to full-fetch (streaming JSON is complex)
            result = await self.query_engine.execute_export_query(
                job.export_config, client_id=job.client_id
            )
            records = result.get("records", [])
            count = result.get("count", len(records))
            local_file_path = FileGenerator.generate_json_file(records, export_dir)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")

        logger.info(
            f"Export completed: run_id={job_run.id}, record_count={count}, "
            f"fields={len(output_fields)}, aliased_fields={aliased_fields}"
        )
        if aliased_fields > 0:
            logger.debug(
                f"Field mappings for run_id={job_run.id}: "
                f"source_fields={source_fields}, output_fields={output_fields}"
            )

        # Upload to cloud storage if configured
        remote_file_path = None
        uploaded_to_cloud = False
        try:
            if self.cloud_storage:
                try:
                    # Generate remote path: exports/{client_id}/{job_id}/{run_id}.{ext}
                    file_ext = FileGenerator.get_file_extension(export_format)
                    remote_file_path = f"exports/{job.client_id}/{job.id}/{job_run.id}{file_ext}"

                    content_type = FileGenerator.get_content_type(export_format)
                    await self.cloud_storage.upload_file(
                        local_file_path, remote_file_path, content_type=content_type
                    )
                    uploaded_to_cloud = True

                    logger.info(
                        f"Export file uploaded to cloud storage: run_id={job_run.id}, "
                        f"remote_path={remote_file_path}"
                    )
                except Exception as e:
                    logger.error(f"Failed to upload file to cloud storage: {e}", exc_info=True)
                    # Continue even if upload fails - file is still available locally
            else:
                logger.warning("Cloud storage not configured. File saved locally only.")

            # Store file metadata in result_metadata
            result_metadata = {
                "count": count,
                "format": export_format,
                "fields": output_fields,
                "worker": worker_id,
            }
            if uploaded_to_cloud:
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
                f"file_location={'cloud' if uploaded_to_cloud else 'local'}"
            )
        finally:
            # Clean up local file only after successful cloud upload
            if uploaded_to_cloud:
                try:
                    os.remove(local_file_path)
                    logger.debug(f"Removed local file: {local_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove local file: {e}")

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

    async def _stream_import_csv(
        self,
        job: JobDefinition,
        job_run: JobRun,
        worker_id: str,
        local_file_path: str,
        source_file: str,
    ) -> None:
        """Import a CSV file in streaming fashion with validation and progress tracking.

        Phase 1: Stream-validate the CSV, writing errors to a JSONL file.
                 If any validation errors, upload error file to S3 and fail the job.
        Phase 2: Stream-import in batches, writing import errors to a JSONL file.
                 Upload error file to S3 if there were import failures.
        """
        assert job.import_config is not None

        import_dir = os.path.dirname(local_file_path) or "/tmp"
        field_mappings = job.import_config.get_field_mappings()

        # ------------------------------------------------------------------
        # Phase 1: Streaming validation
        # ------------------------------------------------------------------
        validation_error_file = os.path.join(import_dir, f"validation_errors_{job_run.id}.jsonl")

        await self.job_run_repository.update_job_statistics(
            job_run.id, {"phase": "validation", "status": "started"}
        )

        total_rows, valid_count, invalid_count = ImportValidator.validate_csv_content_streaming(
            local_file_path,
            job.import_config.entity,
            validation_error_file,
            field_mappings=field_mappings,
        )

        await self.job_run_repository.update_job_statistics(
            job_run.id,
            {
                "phase": "validation",
                "total_rows": total_rows,
                "valid_count": valid_count,
                "invalid_count": invalid_count,
            },
        )

        if invalid_count > 0:
            # Upload validation error file to S3
            error_remote_path = None
            if self.cloud_storage:
                error_remote_path = (
                    f"imports/{job.client_id}/{job.id}/{job_run.id}/validation_errors.jsonl"
                )
                try:
                    await self.cloud_storage.upload_file(
                        validation_error_file,
                        error_remote_path,
                        content_type="application/x-ndjson",
                    )
                except Exception as e:
                    logger.error(f"Failed to upload validation error file: {e}")

            try:
                os.remove(validation_error_file)
            except OSError:
                pass

            await self.job_run_repository.update_status(
                job_run.id,
                JobStatus.FAILED,
                completed_at=datetime.now(UTC),
                error_message=(
                    f"Validation failed: {invalid_count} invalid rows out of {total_rows}"
                ),
                result_metadata={
                    "total_rows": total_rows,
                    "valid_count": valid_count,
                    "invalid_count": invalid_count,
                    "validation_error_file": error_remote_path or validation_error_file,
                },
            )
            logger.info(
                f"Import validation failed: run_id={job_run.id}, "
                f"invalid_count={invalid_count}, total_rows={total_rows}"
            )
            return

        # No validation errors — clean up empty error file
        try:
            os.remove(validation_error_file)
        except OSError:
            pass

        # ------------------------------------------------------------------
        # Phase 2: Streaming import
        # ------------------------------------------------------------------
        import_error_file = os.path.join(import_dir, f"import_errors_{job_run.id}.jsonl")

        imported_count = 0
        updated_count = 0
        deleted_count = 0
        skipped_count = 0
        failed_count = 0
        rows_processed = 0
        last_stats_time = datetime.now(UTC)

        with open(import_error_file, "w", encoding="utf-8") as error_f:
            for batch in FileParser.parse_csv_streaming(local_file_path):
                batch_start_row = rows_processed
                rows_processed += len(batch)

                # Apply field mappings
                if field_mappings:
                    batch = [self._apply_field_mappings(r, field_mappings) for r in batch]

                try:
                    result = await self.saas_client.import_data(
                        job.import_config, client_id=job.client_id, data=batch
                    )

                    imported_count += result.get("imported_count", 0)
                    updated_count += result.get("updated_count", 0)
                    deleted_count += result.get("deleted_count", 0)
                    skipped_count += result.get("skipped_count", 0)
                    failed_count += result.get("failed_count", 0)

                    # Write errors with adjusted row numbers
                    for error in result.get("errors", []):
                        error["row"] = batch_start_row + error.get("row", 0)
                        error_f.write(json.dumps(error) + "\n")

                except Exception as e:
                    logger.error(
                        f"Batch import failed at rows {batch_start_row + 1}-{rows_processed}: {e}",
                        exc_info=True,
                    )
                    failed_count += len(batch)
                    error_f.write(
                        json.dumps(
                            {
                                "row": batch_start_row + 1,
                                "message": f"Batch failed: {str(e)}",
                            }
                        )
                        + "\n"
                    )

                # Update job statistics (time-throttled)
                is_first = rows_processed == len(batch)
                now = datetime.now(UTC)
                elapsed = (now - last_stats_time).total_seconds()
                if is_first or elapsed >= STATS_UPDATE_INTERVAL:
                    await self.job_run_repository.update_job_statistics(
                        job_run.id,
                        {
                            "phase": "import",
                            "rows_processed": rows_processed,
                            "total_rows": total_rows,
                            "imported_count": imported_count,
                            "updated_count": updated_count,
                            "deleted_count": deleted_count,
                            "skipped_count": skipped_count,
                            "failed_count": failed_count,
                        },
                    )
                    last_stats_time = now

        # Final stats update
        await self.job_run_repository.update_job_statistics(
            job_run.id,
            {
                "phase": "import",
                "rows_processed": rows_processed,
                "total_rows": total_rows,
                "imported_count": imported_count,
                "updated_count": updated_count,
                "deleted_count": deleted_count,
                "skipped_count": skipped_count,
                "failed_count": failed_count,
            },
        )

        # Upload import error file if there were errors
        error_remote_path = None
        if failed_count > 0 and self.cloud_storage:
            error_remote_path = f"imports/{job.client_id}/{job.id}/{job_run.id}/import_errors.jsonl"
            try:
                await self.cloud_storage.upload_file(
                    import_error_file,
                    error_remote_path,
                    content_type="application/x-ndjson",
                )
            except Exception as e:
                logger.error(f"Failed to upload import error file: {e}")

        # Clean up local error file
        try:
            os.remove(import_error_file)
        except OSError:
            pass

        # Build result metadata
        result_metadata: dict[str, Any] = {
            "imported_count": imported_count,
            "updated_count": updated_count,
            "deleted_count": deleted_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "total_rows": total_rows,
            "source_file": source_file,
            "worker": worker_id,
        }
        if error_remote_path:
            result_metadata["import_error_file"] = error_remote_path

        await self.job_run_repository.update_status(
            job_run.id,
            JobStatus.SUCCEEDED if failed_count == 0 else JobStatus.FAILED,
            completed_at=datetime.now(UTC),
            result_metadata=result_metadata,
            error_message=f"{failed_count} records failed to import" if failed_count > 0 else None,
        )

        logger.info(
            f"Streaming import completed: run_id={job_run.id}, total_rows={total_rows}, "
            f"imported={imported_count}, updated={updated_count}, "
            f"deleted={deleted_count}, skipped={skipped_count}, failed={failed_count}"
        )

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
            logger.info(
                f"Import job processing file: run_id={job_run.id}, source_file={source_file}, "
                f"entity={job.import_config.entity.value}"
            )

            # Download file from cloud storage if needed
            local_file_path = source_file
            downloaded_temp_file = False

            # If file is in cloud storage, download it first
            if self.cloud_storage and not os.path.exists(source_file):
                try:
                    from app.core.config import get_settings

                    settings = get_settings()
                    temp_dir = settings.export_local_path or "/tmp"
                    os.makedirs(temp_dir, exist_ok=True)
                    local_file_path = os.path.join(
                        temp_dir, f"import_{job_run.id}_{os.path.basename(source_file)}"
                    )

                    logger.info(f"Downloading file from cloud storage: {source_file}")
                    await self.cloud_storage.download_file(source_file, local_file_path)
                    downloaded_temp_file = True
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

            try:
                # CSV files use streaming import (memory-efficient)
                _, ext = os.path.splitext(local_file_path)
                if ext.lower() == ".csv":
                    await self._stream_import_csv(
                        job, job_run, worker_id, local_file_path, source_file
                    )
                    return

                # Non-CSV (JSON) — load all into memory (streaming JSON is complex)
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

                field_mappings = job.import_config.get_field_mappings()
                if field_mappings:
                    data = [self._apply_field_mappings(record, field_mappings) for record in data]

                result = await self.saas_client.import_data(
                    job.import_config, client_id=job.client_id, data=data
                )

                result_metadata: dict[str, Any] = {
                    "imported_count": result.get("imported_count", 0),
                    "updated_count": result.get("updated_count", 0),
                    "deleted_count": result.get("deleted_count", 0),
                    "skipped_count": result.get("skipped_count", 0),
                    "failed_count": result.get("failed_count", 0),
                    "source_file": source_file,
                    "worker": worker_id,
                }
                if result.get("errors"):
                    result_metadata["import_errors"] = result["errors"]

                await self.job_run_repository.update_status(
                    job_run.id,
                    JobStatus.SUCCEEDED if result.get("failed_count", 0) == 0 else JobStatus.FAILED,
                    completed_at=datetime.now(UTC),
                    result_metadata=result_metadata,
                    error_message=f"{result.get('failed_count', 0)} records failed to import"
                    if result.get("failed_count", 0) > 0
                    else None,
                )

                logger.info(
                    f"Job execution completed: run_id={job_run.id}, job_id={job.id}, "
                    f"imported={result.get('imported_count', 0)}, "
                    f"updated={result.get('updated_count', 0)}, "
                    f"failed={result.get('failed_count', 0)}"
                )
            finally:
                # Clean up temp file downloaded from cloud storage
                if downloaded_temp_file and os.path.exists(local_file_path):
                    try:
                        os.remove(local_file_path)
                        logger.debug(f"Cleaned up temp import file: {local_file_path}")
                    except OSError as e:
                        logger.warning(f"Failed to clean up temp import file: {e}")
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
