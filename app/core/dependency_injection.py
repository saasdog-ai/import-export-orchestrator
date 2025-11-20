"""Dependency injection container."""

from typing import Optional

from app.core.config import get_settings
from app.infrastructure.db.database import Database
from app.infrastructure.db.repositories import (
    JobRepository,
    JobRunRepository,
)
from app.infrastructure.query.engine import ExportQueryEngine
from app.infrastructure.queue.factory import get_message_queue as create_message_queue
from app.infrastructure.queue.interface import MessageQueueInterface
from app.infrastructure.scheduling.scheduler import APSchedulerService
from app.infrastructure.saas.client import MockSaaSApiClient
from app.infrastructure.storage.factory import get_cloud_storage as create_cloud_storage
from app.infrastructure.storage.interface import CloudStorageInterface
from app.services.job_runner import JobRunnerService
from app.services.job_service import JobService
from app.services.scheduler_service import SchedulerService

settings = get_settings()

# Global instances (initialized on startup)
_db: Optional[Database] = None
_job_repository: Optional[JobRepository] = None
_job_run_repository: Optional[JobRunRepository] = None
_query_engine: Optional[ExportQueryEngine] = None
_scheduler: Optional[APSchedulerService] = None
_scheduler_service: Optional[SchedulerService] = None
_job_runner: Optional[JobRunnerService] = None
_job_service: Optional[JobService] = None
_saas_client: Optional[MockSaaSApiClient] = None
_cloud_storage: Optional[CloudStorageInterface] = None
_message_queue: Optional[MessageQueueInterface] = None


async def init_dependencies() -> None:
    """Initialize all dependencies."""
    global _db, _job_repository, _job_run_repository, _query_engine
    global _scheduler, _scheduler_service, _job_runner, _job_service, _saas_client, _cloud_storage, _message_queue

    # Database
    _db = Database(settings.database_url)
    await _db.connect()

    # Repositories
    _job_repository = JobRepository(_db)
    _job_run_repository = JobRunRepository(_db)

    # SaaS Client (needed by query engine)
    _saas_client = MockSaaSApiClient()

    # Query Engine
    _query_engine = ExportQueryEngine(_db, _saas_client)

    # Cloud Storage
    _cloud_storage = create_cloud_storage()

    # Message Queue
    _message_queue = create_message_queue()

    # Scheduler
    _scheduler = APSchedulerService(timezone=settings.scheduler_timezone)
    if settings.scheduler_enabled:
        _scheduler.start()

    # Services
    _job_runner = JobRunnerService(
        job_repository=_job_repository,
        job_run_repository=_job_run_repository,
        query_engine=_query_engine,
        saas_client=_saas_client,
        cloud_storage=_cloud_storage,
        message_queue=_message_queue,
        max_workers=settings.job_runner_max_workers,
    )

    _scheduler_service = SchedulerService(
        scheduler=_scheduler,
        job_repository=_job_repository,
        job_run_repository=_job_run_repository,
        job_runner=_job_runner,
        message_queue=_message_queue,
    )

    _job_service = JobService(
        job_repository=_job_repository,
        job_run_repository=_job_run_repository,
        scheduler_service=_scheduler_service,
        job_runner=_job_runner,
        message_queue=_message_queue,
    )


async def shutdown_dependencies() -> None:
    """Shutdown all dependencies."""
    global _scheduler, _db

    if _scheduler:
        _scheduler.shutdown()

    if _db:
        await _db.disconnect()


def get_database() -> Database:
    """Get database instance."""
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_dependencies() first.")
    return _db


def get_job_repository() -> JobRepository:
    """Get job repository instance."""
    if _job_repository is None:
        raise RuntimeError("Job repository not initialized.")
    return _job_repository


def get_job_run_repository() -> JobRunRepository:
    """Get job run repository instance."""
    if _job_run_repository is None:
        raise RuntimeError("Job run repository not initialized.")
    return _job_run_repository


def get_query_engine() -> ExportQueryEngine:
    """Get query engine instance."""
    if _query_engine is None:
        raise RuntimeError("Query engine not initialized.")
    return _query_engine


def get_scheduler() -> APSchedulerService:
    """Get scheduler instance."""
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized.")
    return _scheduler


def get_scheduler_service() -> SchedulerService:
    """Get scheduler service instance."""
    if _scheduler_service is None:
        raise RuntimeError("Scheduler service not initialized.")
    return _scheduler_service


def get_job_runner() -> JobRunnerService:
    """Get job runner instance."""
    if _job_runner is None:
        raise RuntimeError("Job runner not initialized.")
    return _job_runner


def get_job_service() -> JobService:
    """Get job service instance."""
    if _job_service is None:
        raise RuntimeError("Job service not initialized.")
    return _job_service


def get_saas_client() -> MockSaaSApiClient:
    """Get SaaS API client instance."""
    if _saas_client is None:
        raise RuntimeError("SaaS client not initialized.")
    return _saas_client


def get_cloud_storage() -> Optional[CloudStorageInterface]:
    """Get cloud storage instance."""
    return _cloud_storage


def get_message_queue() -> Optional[MessageQueueInterface]:
    """Get message queue instance."""
    return _message_queue

