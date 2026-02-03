"""Repository implementations for database operations."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, update

from app.core.logging import get_logger
from app.domain.entities import (
    JobDefinition,
    JobRun,
    JobStatus,
    JobType,
)
from app.infrastructure.db.database import Database
from app.infrastructure.db.models import (
    JobDefinitionModel,
    JobRunModel,
)

logger = get_logger(__name__)


def _to_naive_utc(dt: datetime | None) -> datetime | None:
    """Convert timezone-aware datetime to naive UTC datetime for database storage."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        # Convert to UTC and remove timezone info
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def _to_aware_utc(dt: datetime | None) -> datetime | None:
    """Convert naive datetime to timezone-aware UTC datetime for domain entities."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Assume naive datetime is UTC and add timezone info
        return dt.replace(tzinfo=UTC)
    return dt


class JobRepository:
    """Repository for job definitions."""

    def __init__(self, db: Database):
        """Initialize repository with database connection."""
        self.db = db

    async def create(self, job: JobDefinition) -> JobDefinition:
        """Create a new job definition."""
        # Log database operation input
        logger.info(
            f"DB create job: job_id={job.id}, client_id={job.client_id}, "
            f"job_type={job.job_type.value}, name={job.name}, enabled={job.enabled}"
        )

        async with self.db.transaction() as session:
            db_job = JobDefinitionModel(
                id=job.id,
                client_id=job.client_id,
                name=job.name,
                job_type=job.job_type.value,
                export_config=job.export_config.model_dump() if job.export_config else None,
                import_config=job.import_config.model_dump() if job.import_config else None,
                cron_schedule=job.cron_schedule,
                enabled=job.enabled,
                created_at=_to_naive_utc(job.created_at),
                updated_at=_to_naive_utc(job.updated_at),
            )
            session.add(db_job)
            await session.flush()  # Flush to get ID, but don't commit yet
            await session.refresh(db_job)
            result = self._model_to_entity(db_job)

            # Log database operation output
            logger.info(
                f"DB job created: job_id={result.id}, client_id={result.client_id}, "
                f"created_at={result.created_at}"
            )

            return result

    async def get_by_id(self, job_id: UUID) -> JobDefinition | None:
        """Get job definition by ID."""
        # Log database operation input
        logger.debug(f"DB get job by id: job_id={job_id}")

        async with self.db.async_session_maker() as session:
            result = await session.execute(
                select(JobDefinitionModel).where(JobDefinitionModel.id == job_id)
            )
            db_job = result.scalar_one_or_none()
            entity = self._model_to_entity(db_job) if db_job else None

            # Log database operation output
            if entity:
                logger.debug(
                    f"DB job found: job_id={job_id}, client_id={entity.client_id}, "
                    f"job_type={entity.job_type.value}"
                )
            else:
                logger.debug(f"DB job not found: job_id={job_id}")

            return entity

    async def get_by_client_id(
        self,
        client_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        job_type: str | None = None,
        entity: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[JobDefinition], int]:
        """Get job definitions for a client with pagination and filtering.

        Returns:
            Tuple of (jobs list, total count)
        """
        # Log database operation input
        logger.debug(
            f"DB get jobs by client: client_id={client_id}, "
            f"start_date={start_date}, end_date={end_date}, "
            f"job_type={job_type}, entity={entity}, page={page}, page_size={page_size}"
        )

        async with self.db.async_session_maker() as session:
            from sqlalchemy import func

            query = select(JobDefinitionModel).where(JobDefinitionModel.client_id == client_id)

            # Apply date filters (convert timezone-aware to naive UTC for comparison)
            if start_date:
                query = query.where(JobDefinitionModel.created_at >= _to_naive_utc(start_date))
            if end_date:
                query = query.where(JobDefinitionModel.created_at <= _to_naive_utc(end_date))

            # Apply job type filter
            if job_type:
                query = query.where(JobDefinitionModel.job_type == job_type)

            # Apply entity filter (search in JSON config)
            if entity:
                from sqlalchemy import String, cast

                # Filter by entity in export_config or import_config using PostgreSQL JSON operators
                query = query.where(
                    (cast(JobDefinitionModel.export_config["entity"], String) == f'"{entity}"')
                    | (cast(JobDefinitionModel.import_config["entity"], String) == f'"{entity}"')
                )

            # Get total count before pagination
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await session.execute(count_query)
            total_count = total_result.scalar() or 0

            # Apply pagination and sorting
            offset = (page - 1) * page_size
            query = query.order_by(JobDefinitionModel.created_at.desc())
            query = query.offset(offset).limit(page_size)

            result = await session.execute(query)
            db_jobs = result.scalars().all()
            jobs = [self._model_to_entity(db_job) for db_job in db_jobs]

            # Log database operation output
            logger.debug(
                f"DB jobs retrieved: client_id={client_id}, count={len(jobs)}, total={total_count}"
            )

            return jobs, total_count

    async def get_enabled_scheduled_jobs(self) -> list[JobDefinition]:
        """Get all enabled jobs with cron schedules."""
        async with self.db.async_session_maker() as session:
            result = await session.execute(
                select(JobDefinitionModel).where(
                    JobDefinitionModel.enabled == True,  # noqa: E712
                    JobDefinitionModel.cron_schedule.isnot(None),
                )
            )
            db_jobs = result.scalars().all()
            return [self._model_to_entity(db_job) for db_job in db_jobs]

    async def update(self, job: JobDefinition) -> JobDefinition:
        """Update a job definition."""
        # Log database operation input
        logger.info(
            f"DB update job: job_id={job.id}, client_id={job.client_id}, "
            f"name={job.name}, enabled={job.enabled}, "
            f"has_cron_schedule={'yes' if job.cron_schedule else 'no'}"
        )

        async with self.db.transaction() as session:
            await session.execute(
                update(JobDefinitionModel)
                .where(JobDefinitionModel.id == job.id)
                .values(
                    name=job.name,
                    job_type=job.job_type.value,
                    export_config=job.export_config.model_dump() if job.export_config else None,
                    import_config=job.import_config.model_dump() if job.import_config else None,
                    cron_schedule=job.cron_schedule,
                    enabled=job.enabled,
                    updated_at=_to_naive_utc(datetime.now(UTC)),
                )
            )
            # Refresh to get updated entity
            await session.flush()
            result = await session.execute(
                select(JobDefinitionModel).where(JobDefinitionModel.id == job.id)
            )
            db_job = result.scalar_one()
            entity = self._model_to_entity(db_job)

            # Log database operation output
            logger.info(f"DB job updated: job_id={entity.id}, updated_at={entity.updated_at}")

            return entity

    async def delete(self, job_id: UUID) -> bool:
        """Delete a job definition and all its runs."""
        logger.info(f"DB delete job: job_id={job_id}")

        async with self.db.transaction() as session:
            # First delete all job runs for this job
            await session.execute(delete(JobRunModel).where(JobRunModel.job_id == job_id))
            # Then delete the job itself
            result = await session.execute(
                delete(JobDefinitionModel).where(JobDefinitionModel.id == job_id)
            )
            deleted = result.rowcount > 0

            logger.info(f"DB job deleted: job_id={job_id}, success={deleted}")
            return bool(deleted)

    def _model_to_entity(self, db_job: JobDefinitionModel) -> JobDefinition:
        """Convert database model to domain entity."""
        from app.domain.entities import ExportConfig, ImportConfig

        return JobDefinition(
            id=db_job.id,  # type: ignore[arg-type]
            client_id=db_job.client_id,  # type: ignore[arg-type]
            name=db_job.name,  # type: ignore[arg-type]
            job_type=JobType(db_job.job_type),
            export_config=ExportConfig(**db_job.export_config) if db_job.export_config else None,
            import_config=ImportConfig(**db_job.import_config) if db_job.import_config else None,
            cron_schedule=db_job.cron_schedule,  # type: ignore[arg-type]
            enabled=db_job.enabled,  # type: ignore[arg-type]
            created_at=_to_aware_utc(db_job.created_at),  # type: ignore[arg-type]
            updated_at=_to_aware_utc(db_job.updated_at),  # type: ignore[arg-type]
        )


class JobRunRepository:
    """Repository for job runs."""

    def __init__(self, db: Database):
        """Initialize repository with database connection."""
        self.db = db

    async def create(self, job_run: JobRun) -> JobRun:
        """Create a new job run."""
        # Log database operation input
        logger.info(
            f"DB create job run: run_id={job_run.id}, job_id={job_run.job_id}, "
            f"status={job_run.status.value}"
        )

        async with self.db.transaction() as session:
            db_run = JobRunModel(
                id=job_run.id,
                job_id=job_run.job_id,
                status=job_run.status.value,
                started_at=_to_naive_utc(job_run.started_at),
                completed_at=_to_naive_utc(job_run.completed_at),
                error_message=job_run.error_message,
                result_metadata=job_run.result_metadata,
                created_at=_to_naive_utc(job_run.created_at),
                updated_at=_to_naive_utc(job_run.updated_at),
            )
            session.add(db_run)
            await session.flush()  # Flush to get ID, but don't commit yet
            await session.refresh(db_run)
            result = self._model_to_entity(db_run)

            # Log database operation output
            logger.info(
                f"DB job run created: run_id={result.id}, job_id={result.job_id}, "
                f"status={result.status.value}, created_at={result.created_at}"
            )

            return result

    async def get_by_id(self, run_id: UUID) -> JobRun | None:
        """Get job run by ID."""
        # Log database operation input
        logger.debug(f"DB get job run by id: run_id={run_id}")

        async with self.db.async_session_maker() as session:
            result = await session.execute(select(JobRunModel).where(JobRunModel.id == run_id))
            db_run = result.scalar_one_or_none()
            entity = self._model_to_entity(db_run) if db_run else None

            # Log database operation output
            if entity:
                logger.debug(
                    f"DB job run found: run_id={run_id}, job_id={entity.job_id}, "
                    f"status={entity.status.value}"
                )
            else:
                logger.debug(f"DB job run not found: run_id={run_id}")

            return entity

    async def get_by_job_id(
        self,
        job_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[JobRun]:
        """Get all runs for a job, optionally filtered by date range."""
        # Log database operation input
        logger.debug(
            f"DB get job runs by job_id: job_id={job_id}, "
            f"start_date={start_date}, end_date={end_date}"
        )

        async with self.db.async_session_maker() as session:
            query = select(JobRunModel).where(JobRunModel.job_id == job_id)

            # Apply date filters (convert timezone-aware to naive UTC for comparison)
            if start_date:
                query = query.where(JobRunModel.created_at >= _to_naive_utc(start_date))
            if end_date:
                query = query.where(JobRunModel.created_at <= _to_naive_utc(end_date))

            result = await session.execute(query.order_by(JobRunModel.created_at.desc()))
            db_runs = result.scalars().all()
            runs = [self._model_to_entity(db_run) for db_run in db_runs]

            # Log database operation output
            logger.debug(f"DB job runs retrieved: job_id={job_id}, count={len(runs)}")

            return runs

    async def update_status(
        self,
        run_id: UUID,
        status: JobStatus,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        error_message: str | None = None,
        result_metadata: dict | None = None,
    ) -> JobRun:
        """Update job run status."""
        # Log database operation input
        logger.info(
            f"DB update job run status: run_id={run_id}, status={status.value}, "
            f"started_at={started_at}, completed_at={completed_at}, "
            f"has_error={'yes' if error_message else 'no'}, "
            f"has_metadata={'yes' if result_metadata else 'no'}"
        )

        async with self.db.transaction() as session:
            update_values: dict[str, Any] = {
                "status": status.value,
                "updated_at": _to_naive_utc(datetime.now(UTC)),
            }
            if started_at:
                update_values["started_at"] = _to_naive_utc(started_at)
            if completed_at:
                update_values["completed_at"] = _to_naive_utc(completed_at)
            if error_message:
                update_values["error_message"] = error_message
            if result_metadata:
                update_values["result_metadata"] = result_metadata

            await session.execute(
                update(JobRunModel).where(JobRunModel.id == run_id).values(**update_values)
            )
            # Refresh to get updated entity
            await session.flush()
            result = await session.execute(select(JobRunModel).where(JobRunModel.id == run_id))
            db_run = result.scalar_one()
            entity = self._model_to_entity(db_run)

            # Log database operation output
            logger.info(
                f"DB job run status updated: run_id={run_id}, status={entity.status.value}, "
                f"updated_at={entity.updated_at}"
            )

            return entity

    async def update_job_statistics(self, run_id: UUID, statistics: dict[str, Any]) -> None:
        """Update job run statistics (lightweight single-column UPDATE)."""
        async with self.db.async_session_maker() as session:
            await session.execute(
                update(JobRunModel)
                .where(JobRunModel.id == run_id)
                .values(job_statistics=statistics)
            )
            await session.commit()

    def _model_to_entity(self, db_run: JobRunModel) -> JobRun:
        """Convert database model to domain entity."""
        return JobRun(
            id=db_run.id,  # type: ignore[arg-type]
            job_id=db_run.job_id,  # type: ignore[arg-type]
            status=JobStatus(db_run.status),
            started_at=_to_aware_utc(db_run.started_at),  # type: ignore[arg-type]
            completed_at=_to_aware_utc(db_run.completed_at),  # type: ignore[arg-type]
            error_message=db_run.error_message,  # type: ignore[arg-type]
            result_metadata=db_run.result_metadata,  # type: ignore[arg-type]
            job_statistics=db_run.job_statistics,  # type: ignore[arg-type]
            created_at=_to_aware_utc(db_run.created_at),  # type: ignore[arg-type]
            updated_at=_to_aware_utc(db_run.updated_at),  # type: ignore[arg-type]
        )
