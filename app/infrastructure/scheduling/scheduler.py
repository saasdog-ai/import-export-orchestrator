"""Pluggable scheduler implementation using APScheduler."""

from datetime import datetime
from typing import Callable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.logging import get_logger

logger = get_logger(__name__)


class SchedulerInterface:
    """Interface for scheduler implementations."""

    def add_cron_job(
        self,
        func: Callable,
        cron_expression: str,
        job_id: str,
        *args: any,
        **kwargs: any,
    ) -> None:
        """Add a cron-scheduled job."""
        raise NotImplementedError

    def remove_job(self, job_id: str) -> None:
        """Remove a scheduled job."""
        raise NotImplementedError

    def start(self) -> None:
        """Start the scheduler."""
        raise NotImplementedError

    def shutdown(self) -> None:
        """Shutdown the scheduler."""
        raise NotImplementedError


class APSchedulerService(SchedulerInterface):
    """APScheduler-based scheduler implementation."""

    def __init__(self, timezone: str = "UTC"):
        """Initialize scheduler."""
        self.timezone = timezone
        self.scheduler: Optional[AsyncIOScheduler] = None

    def start(self) -> None:
        """Start the scheduler."""
        if self.scheduler is None:
            self.scheduler = AsyncIOScheduler(timezone=self.timezone)
            self.scheduler.start()
            logger.info("Scheduler started")

    def shutdown(self) -> None:
        """Shutdown the scheduler."""
        if self.scheduler:
            self.scheduler.shutdown(wait=True)
            self.scheduler = None
            logger.info("Scheduler shut down")

    def add_cron_job(
        self,
        func: Callable,
        cron_expression: str,
        job_id: str,
        *args: any,
        **kwargs: any,
    ) -> None:
        """Add a cron-scheduled job."""
        if not self.scheduler:
            raise RuntimeError("Scheduler not started. Call start() first.")

        try:
            # Parse cron expression (format: "minute hour day month day_of_week")
            parts = cron_expression.split()
            if len(parts) != 5:
                raise ValueError(f"Invalid cron expression: {cron_expression}")

            minute, hour, day, month, day_of_week = parts

            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                timezone=self.timezone,
            )

            # Remove job if it exists
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)

            self.scheduler.add_job(
                func,
                trigger=trigger,
                id=job_id,
                args=args,
                kwargs=kwargs,
                replace_existing=True,
            )
            logger.info(f"Added cron job '{job_id}' with schedule '{cron_expression}'")
        except Exception as e:
            logger.error(f"Failed to add cron job '{job_id}': {e}")
            raise

    def remove_job(self, job_id: str) -> None:
        """Remove a scheduled job."""
        if not self.scheduler:
            return

        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"Removed cron job '{job_id}'")
        except Exception as e:
            logger.error(f"Failed to remove cron job '{job_id}': {e}")

    def get_job(self, job_id: str) -> Optional[any]:
        """Get a scheduled job by ID."""
        if not self.scheduler:
            return None
        return self.scheduler.get_job(job_id)

