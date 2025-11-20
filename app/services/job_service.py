"""Service for managing job definitions and runs."""

from datetime import datetime
from uuid import UUID

from app.core.logging import get_logger
from app.domain.entities import JobDefinition, JobRun, JobStatus
from app.infrastructure.db.repositories import JobRepository, JobRunRepository
from app.infrastructure.queue.interface import MessageQueueInterface
from app.services.job_runner import JobRunnerService
from app.services.scheduler_service import SchedulerService

logger = get_logger(__name__)


class JobService:
    """Service for job management operations."""

    def __init__(
        self,
        job_repository: JobRepository,
        job_run_repository: JobRunRepository,
        scheduler_service: SchedulerService,
        job_runner: JobRunnerService,
        message_queue: MessageQueueInterface | None = None,
    ):
        """Initialize job service."""
        self.job_repository = job_repository
        self.job_run_repository = job_run_repository
        self.scheduler_service = scheduler_service
        self.job_runner = job_runner
        self.message_queue = message_queue

    async def create_job(self, job: JobDefinition) -> JobDefinition:
        """Create a new job definition."""
        created_job = await self.job_repository.create(job)

        # If job has a cron schedule and is enabled, schedule it
        if created_job.cron_schedule and created_job.enabled:
            await self.scheduler_service.schedule_job(created_job)

        logger.info(f"Created job '{created_job.name}' (ID: {created_job.id})")
        return created_job

    async def get_job(self, job_id: UUID) -> JobDefinition:
        """Get a job definition by ID."""
        job = await self.job_repository.get_by_id(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        return job

    async def get_jobs_by_client(
        self,
        client_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[JobDefinition]:
        """Get all jobs for a client, optionally filtered by date range."""
        return await self.job_repository.get_by_client_id(
            client_id, start_date=start_date, end_date=end_date
        )

    async def update_job(self, job: JobDefinition) -> JobDefinition:
        """Update a job definition."""
        existing = await self.job_repository.get_by_id(job.id)
        if not existing:
            raise ValueError(f"Job not found: {job.id}")

        updated_job = await self.job_repository.update(job)

        # Update scheduler if cron schedule changed
        await self.scheduler_service.unschedule_job(job.id)
        if updated_job.cron_schedule and updated_job.enabled:
            await self.scheduler_service.schedule_job(updated_job)

        logger.info(f"Updated job '{updated_job.name}' (ID: {updated_job.id})")
        return updated_job

    async def run_job(self, job_id: UUID) -> JobRun:
        """Manually trigger a job run."""
        job = await self.get_job(job_id)

        # Create job run in database
        job_run = JobRun(
            job_id=job.id,
            status=JobStatus.PENDING,
        )
        created_run = await self.job_run_repository.create(job_run)

        # Send message to external queue (SQS, Azure Queue, or GCP Pub/Sub)
        if self.message_queue:
            message_body = {
                "job_id": str(job.id),
                "job_run_id": str(created_run.id),
                "job_type": job.job_type.value,
            }
            await self.message_queue.send_message(message_body)
            logger.info(
                f"Queued job run for job '{job.name}' (Run ID: {created_run.id}) to message queue"
            )
        else:
            # Fallback to in-memory queue if no external queue configured
            await self.job_runner.queue_job_run(job, created_run)
            logger.warning(
                f"No external queue configured. Using in-memory queue (not recommended for production). "
                f"Queued job run for job '{job.name}' (Run ID: {created_run.id})"
            )

        return created_run

    async def get_job_run(self, run_id: UUID) -> JobRun:
        """Get a job run by ID."""
        job_run = await self.job_run_repository.get_by_id(run_id)
        if not job_run:
            raise ValueError(f"Job run not found: {run_id}")
        return job_run

    async def get_job_runs(
        self,
        job_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[JobRun]:
        """Get all runs for a job, optionally filtered by date range."""
        return await self.job_run_repository.get_by_job_id(
            job_id, start_date=start_date, end_date=end_date
        )
