"""Unit tests for scheduler service with mocked dependencies."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.entities import (
    ExportConfig,
    ExportEntity,
    JobDefinition,
    JobRun,
    JobStatus,
    JobType,
)
from app.infrastructure.queue.interface import MessageQueueInterface
from app.infrastructure.scheduling.scheduler import SchedulerInterface
from app.services.scheduler_service import SchedulerService


@pytest.fixture
def mock_scheduler():
    """Create a mocked scheduler."""
    scheduler = MagicMock(spec=SchedulerInterface)
    return scheduler


@pytest.fixture
def mock_job_repository():
    """Create a mocked job repository."""
    return AsyncMock()


@pytest.fixture
def mock_job_run_repository():
    """Create a mocked job run repository."""
    return AsyncMock()


@pytest.fixture
def mock_job_runner():
    """Create a mocked job runner."""
    return AsyncMock()


@pytest.fixture
def mock_message_queue():
    """Create a mocked message queue."""
    queue = MagicMock(spec=MessageQueueInterface)
    queue.send_message = AsyncMock(return_value="message-id")
    return queue


@pytest.fixture
def scheduler_service(
    mock_scheduler,
    mock_job_repository,
    mock_job_run_repository,
    mock_job_runner,
    mock_message_queue,
):
    """Create a scheduler service with mocked dependencies."""
    return SchedulerService(
        scheduler=mock_scheduler,
        job_repository=mock_job_repository,
        job_run_repository=mock_job_run_repository,
        job_runner=mock_job_runner,
        message_queue=mock_message_queue,
    )


@pytest.mark.asyncio
async def test_schedule_job_success(scheduler_service, mock_scheduler, mock_message_queue):
    """Test scheduling a job successfully."""
    # Setup
    job = JobDefinition(
        id=uuid4(),
        client_id=uuid4(),
        name="Scheduled Job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(entity=ExportEntity.BILL, fields=["id"]),
        cron_schedule="0 0 * * *",
        enabled=True,
    )

    # Execute
    await scheduler_service.schedule_job(job)

    # Verify
    mock_scheduler.add_cron_job.assert_called_once()
    # Verify the cron schedule and job ID were passed
    call_args = mock_scheduler.add_cron_job.call_args
    assert call_args[0][1] == "0 0 * * *"  # cron_schedule
    assert call_args[0][2] == str(job.id)  # job_id


@pytest.mark.asyncio
async def test_schedule_job_no_cron(scheduler_service, mock_scheduler):
    """Test scheduling a job without cron schedule."""
    # Setup
    job = JobDefinition(
        id=uuid4(),
        client_id=uuid4(),
        name="No Cron Job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(entity=ExportEntity.BILL, fields=["id"]),
        cron_schedule=None,  # No cron
        enabled=True,
    )

    # Execute
    await scheduler_service.schedule_job(job)

    # Verify scheduler was not called
    mock_scheduler.add_cron_job.assert_not_called()


@pytest.mark.asyncio
async def test_schedule_job_disabled(scheduler_service, mock_scheduler):
    """Test scheduling a disabled job."""
    # Setup
    job = JobDefinition(
        id=uuid4(),
        client_id=uuid4(),
        name="Disabled Job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(entity=ExportEntity.BILL, fields=["id"]),
        cron_schedule="0 0 * * *",
        enabled=False,  # Disabled
    )

    # Execute
    await scheduler_service.schedule_job(job)

    # Verify scheduler was not called
    mock_scheduler.add_cron_job.assert_not_called()


@pytest.mark.asyncio
async def test_schedule_job_with_message_queue(
    scheduler_service,
    mock_scheduler,
    mock_job_run_repository,
    mock_message_queue,
):
    """Test scheduled job execution with message queue."""
    # Setup
    job = JobDefinition(
        id=uuid4(),
        client_id=uuid4(),
        name="Scheduled Job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(entity=ExportEntity.BILL, fields=["id"]),
        cron_schedule="0 0 * * *",
        enabled=True,
    )

    # Mock job run creation
    job_run = JobRun(
        id=uuid4(),
        job_id=job.id,
        status=JobStatus.PENDING,
    )
    mock_job_run_repository.create = AsyncMock(return_value=job_run)

    # Schedule the job
    await scheduler_service.schedule_job(job)

    # Get the scheduled function and execute it
    scheduled_func = mock_scheduler.add_cron_job.call_args[0][0]
    await scheduled_func()

    # Verify
    mock_job_run_repository.create.assert_called_once()
    mock_message_queue.send_message.assert_called_once()
    # Verify message contains correct data
    message_call = mock_message_queue.send_message.call_args[0][0]
    assert message_call["job_id"] == str(job.id)
    assert message_call["job_run_id"] == str(job_run.id)


@pytest.mark.asyncio
async def test_schedule_job_without_message_queue(
    mock_scheduler,
    mock_job_repository,
    mock_job_run_repository,
    mock_job_runner,
):
    """Test scheduled job execution without message queue (fallback to in-memory)."""
    # Create service without message queue
    scheduler_service = SchedulerService(
        scheduler=mock_scheduler,
        job_repository=mock_job_repository,
        job_run_repository=mock_job_run_repository,
        job_runner=mock_job_runner,
        message_queue=None,  # No queue
    )

    # Setup
    job = JobDefinition(
        id=uuid4(),
        client_id=uuid4(),
        name="Scheduled Job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(entity=ExportEntity.BILL, fields=["id"]),
        cron_schedule="0 0 * * *",
        enabled=True,
    )

    # Mock job run creation
    job_run = JobRun(
        id=uuid4(),
        job_id=job.id,
        status=JobStatus.PENDING,
    )
    mock_job_run_repository.create = AsyncMock(return_value=job_run)
    mock_job_runner.queue_job_run = AsyncMock()

    # Schedule the job
    await scheduler_service.schedule_job(job)

    # Get the scheduled function and execute it
    scheduled_func = mock_scheduler.add_cron_job.call_args[0][0]
    await scheduled_func()

    # Verify
    mock_job_run_repository.create.assert_called_once()
    mock_job_runner.queue_job_run.assert_called_once_with(job, job_run)


@pytest.mark.asyncio
async def test_unschedule_job(scheduler_service, mock_scheduler):
    """Test unscheduling a job."""
    # Setup
    job_id = uuid4()

    # Execute
    await scheduler_service.unschedule_job(job_id)

    # Verify
    mock_scheduler.remove_job.assert_called_once_with(str(job_id))


@pytest.mark.asyncio
async def test_reload_all_scheduled_jobs(scheduler_service, mock_job_repository, mock_scheduler):
    """Test reloading all scheduled jobs."""
    # Setup
    jobs = [
        JobDefinition(
            id=uuid4(),
            client_id=uuid4(),
            name="Job 1",
            job_type=JobType.EXPORT,
            export_config=ExportConfig(entity=ExportEntity.BILL, fields=["id"]),
            cron_schedule="0 0 * * *",
            enabled=True,
        ),
        JobDefinition(
            id=uuid4(),
            client_id=uuid4(),
            name="Job 2",
            job_type=JobType.EXPORT,
            export_config=ExportConfig(entity=ExportEntity.BILL, fields=["id"]),
            cron_schedule="0 1 * * *",
            enabled=True,
        ),
    ]

    mock_job_repository.get_enabled_scheduled_jobs = AsyncMock(return_value=jobs)

    # Execute
    await scheduler_service.reload_all_scheduled_jobs()

    # Verify
    mock_job_repository.get_enabled_scheduled_jobs.assert_called_once()
    assert mock_scheduler.add_cron_job.call_count == 2
