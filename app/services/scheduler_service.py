"""Service for managing job scheduling."""

from typing import Optional
from uuid import UUID

from app.core.logging import get_logger
from app.domain.entities import JobDefinition
from app.infrastructure.db.repositories import JobRepository, JobRunRepository
from app.infrastructure.queue.interface import MessageQueueInterface
from app.infrastructure.scheduling.scheduler import SchedulerInterface
from app.services.job_runner import JobRunnerService

logger = get_logger(__name__)


class SchedulerService:
    """Service for managing scheduled jobs."""

    def __init__(
        self,
        scheduler: SchedulerInterface,
        job_repository: JobRepository,
        job_run_repository: JobRunRepository,
        job_runner: JobRunnerService,
        message_queue: Optional[MessageQueueInterface] = None,
    ):
        """Initialize scheduler service."""
        self.scheduler = scheduler
        self.job_repository = job_repository
        self.job_run_repository = job_run_repository
        self.job_runner = job_runner
        self.message_queue = message_queue

    async def schedule_job(self, job: JobDefinition) -> None:
        """Schedule a job for automatic execution."""
        if not job.cron_schedule:
            logger.warning(f"Job {job.id} has no cron schedule, skipping")
            return

        if not job.enabled:
            logger.warning(f"Job {job.id} is disabled, skipping")
            return

        # Create wrapper function that will be called by scheduler
        async def execute_scheduled_job():
            from app.domain.entities import JobRun, JobStatus

            logger.info(f"Executing scheduled job {job.id} ({job.name})")

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
                    f"Queued scheduled job run for job '{job.name}' (Run ID: {created_run.id}) to message queue"
                )
            else:
                # Fallback to in-memory queue if no external queue configured
                await self.job_runner.queue_job_run(job, created_run)
                logger.warning(
                    f"No external queue configured. Using in-memory queue for scheduled job '{job.name}'"
                )

        # Schedule the job
        job_id_str = str(job.id)
        self.scheduler.add_cron_job(
            execute_scheduled_job,
            job.cron_schedule,
            job_id_str,
        )
        logger.info(f"Scheduled job {job.id} with cron '{job.cron_schedule}'")

    async def unschedule_job(self, job_id: UUID) -> None:
        """Unschedule a job."""
        job_id_str = str(job_id)
        self.scheduler.remove_job(job_id_str)
        logger.info(f"Unscheduled job {job_id}")

    async def reload_all_scheduled_jobs(self) -> None:
        """Reload all enabled scheduled jobs from database."""
        jobs = await self.job_repository.get_enabled_scheduled_jobs()
        for job in jobs:
            await self.schedule_job(job)
        logger.info(f"Reloaded {len(jobs)} scheduled jobs")

