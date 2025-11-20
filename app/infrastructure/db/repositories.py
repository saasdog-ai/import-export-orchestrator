"""Repository implementations for database operations."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update

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
        async with self.db.async_session_maker() as session:
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
            await session.commit()
            await session.refresh(db_job)
            return self._model_to_entity(db_job)

    async def get_by_id(self, job_id: UUID) -> JobDefinition | None:
        """Get job definition by ID."""
        async with self.db.async_session_maker() as session:
            result = await session.execute(
                select(JobDefinitionModel).where(JobDefinitionModel.id == job_id)
            )
            db_job = result.scalar_one_or_none()
            return self._model_to_entity(db_job) if db_job else None

    async def get_by_client_id(
        self,
        client_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[JobDefinition]:
        """Get all job definitions for a client, optionally filtered by date range."""
        async with self.db.async_session_maker() as session:
            query = select(JobDefinitionModel).where(JobDefinitionModel.client_id == client_id)

            # Apply date filters (convert timezone-aware to naive UTC for comparison)
            if start_date:
                query = query.where(JobDefinitionModel.created_at >= _to_naive_utc(start_date))
            if end_date:
                query = query.where(JobDefinitionModel.created_at <= _to_naive_utc(end_date))

            result = await session.execute(query.order_by(JobDefinitionModel.created_at.desc()))
            db_jobs = result.scalars().all()
            return [self._model_to_entity(db_job) for db_job in db_jobs]

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
        async with self.db.async_session_maker() as session:
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
            await session.commit()
            return await self.get_by_id(job.id)

    def _model_to_entity(self, db_job: JobDefinitionModel) -> JobDefinition:
        """Convert database model to domain entity."""
        from app.domain.entities import ExportConfig, ImportConfig

        return JobDefinition(
            id=db_job.id,
            client_id=db_job.client_id,
            name=db_job.name,
            job_type=JobType(db_job.job_type),
            export_config=ExportConfig(**db_job.export_config) if db_job.export_config else None,
            import_config=ImportConfig(**db_job.import_config) if db_job.import_config else None,
            cron_schedule=db_job.cron_schedule,
            enabled=db_job.enabled,
            created_at=_to_aware_utc(db_job.created_at),
            updated_at=_to_aware_utc(db_job.updated_at),
        )


class JobRunRepository:
    """Repository for job runs."""

    def __init__(self, db: Database):
        """Initialize repository with database connection."""
        self.db = db

    async def create(self, job_run: JobRun) -> JobRun:
        """Create a new job run."""
        async with self.db.async_session_maker() as session:
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
            await session.commit()
            await session.refresh(db_run)
            return self._model_to_entity(db_run)

    async def get_by_id(self, run_id: UUID) -> JobRun | None:
        """Get job run by ID."""
        async with self.db.async_session_maker() as session:
            result = await session.execute(select(JobRunModel).where(JobRunModel.id == run_id))
            db_run = result.scalar_one_or_none()
            return self._model_to_entity(db_run) if db_run else None

    async def get_by_job_id(
        self,
        job_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[JobRun]:
        """Get all runs for a job, optionally filtered by date range."""
        async with self.db.async_session_maker() as session:
            query = select(JobRunModel).where(JobRunModel.job_id == job_id)

            # Apply date filters (convert timezone-aware to naive UTC for comparison)
            if start_date:
                query = query.where(JobRunModel.created_at >= _to_naive_utc(start_date))
            if end_date:
                query = query.where(JobRunModel.created_at <= _to_naive_utc(end_date))

            result = await session.execute(query.order_by(JobRunModel.created_at.desc()))
            db_runs = result.scalars().all()
            return [self._model_to_entity(db_run) for db_run in db_runs]

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
        async with self.db.async_session_maker() as session:
            update_values = {
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
            await session.commit()
            return await self.get_by_id(run_id)

    def _model_to_entity(self, db_run: JobRunModel) -> JobRun:
        """Convert database model to domain entity."""
        return JobRun(
            id=db_run.id,
            job_id=db_run.job_id,
            status=JobStatus(db_run.status),
            started_at=_to_aware_utc(db_run.started_at),
            completed_at=_to_aware_utc(db_run.completed_at),
            error_message=db_run.error_message,
            result_metadata=db_run.result_metadata,
            created_at=_to_aware_utc(db_run.created_at),
            updated_at=_to_aware_utc(db_run.updated_at),
        )
