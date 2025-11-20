"""Unit tests for services with mocked dependencies."""

from unittest.mock import AsyncMock
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
from app.services.job_service import JobService


@pytest.fixture
def mock_job_repository():
    """Create a mocked job repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_job_run_repository():
    """Create a mocked job run repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_scheduler_service():
    """Create a mocked scheduler service."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_job_runner():
    """Create a mocked job runner."""
    runner = AsyncMock()
    return runner


@pytest.fixture
def mock_message_queue():
    """Create a mocked message queue."""
    queue = AsyncMock()
    return queue


@pytest.fixture
def job_service(
    mock_job_repository,
    mock_job_run_repository,
    mock_scheduler_service,
    mock_job_runner,
    mock_message_queue,
):
    """Create a job service with mocked dependencies."""
    return JobService(
        job_repository=mock_job_repository,
        job_run_repository=mock_job_run_repository,
        scheduler_service=mock_scheduler_service,
        job_runner=mock_job_runner,
        message_queue=mock_message_queue,
    )


@pytest.mark.asyncio
async def test_create_job(job_service, mock_job_repository, test_client_id):
    """Test creating a job via service."""
    export_config = ExportConfig(
        entity=ExportEntity.BILL,
        fields=["id", "amount", "date"],
        limit=100,
    )
    job = JobDefinition(
        id=uuid4(),
        client_id=test_client_id,
        name="Test Export Job",
        job_type=JobType.EXPORT,
        export_config=export_config,
        enabled=True,
    )

    # Mock repository response
    mock_job_repository.create = AsyncMock(return_value=job)

    # Execute
    created_job = await job_service.create_job(job)

    # Verify
    assert created_job.id == job.id
    assert created_job.name == job.name
    mock_job_repository.create.assert_called_once_with(job)


@pytest.mark.asyncio
async def test_get_job(job_service, mock_job_repository):
    """Test getting a job by ID."""
    job_id = uuid4()
    job = JobDefinition(
        id=job_id,
        client_id=uuid4(),
        name="Test Job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(entity=ExportEntity.BILL, fields=["id"]),
    )

    # Mock repository response
    mock_job_repository.get_by_id = AsyncMock(return_value=job)

    # Execute
    retrieved_job = await job_service.get_job(job_id)

    # Verify
    assert retrieved_job is not None
    assert retrieved_job.id == job_id
    mock_job_repository.get_by_id.assert_called_once_with(job_id)


@pytest.mark.asyncio
async def test_get_jobs_by_client(job_service, mock_job_repository, test_client_id):
    """Test getting jobs by client ID."""
    jobs = [
        JobDefinition(
            id=uuid4(),
            client_id=test_client_id,
            name="Job 1",
            job_type=JobType.EXPORT,
            export_config=ExportConfig(entity=ExportEntity.BILL, fields=["id"]),
        ),
        JobDefinition(
            id=uuid4(),
            client_id=test_client_id,
            name="Job 2",
            job_type=JobType.EXPORT,
            export_config=ExportConfig(entity=ExportEntity.BILL, fields=["id"]),
        ),
    ]

    # Mock repository response
    mock_job_repository.get_by_client_id = AsyncMock(return_value=jobs)

    # Execute
    result = await job_service.get_jobs_by_client(test_client_id)

    # Verify
    assert len(result) == 2
    assert all(job.client_id == test_client_id for job in result)
    mock_job_repository.get_by_client_id.assert_called_once_with(
        test_client_id, start_date=None, end_date=None
    )


@pytest.mark.asyncio
async def test_run_job(
    job_service, mock_job_repository, mock_job_run_repository, mock_message_queue
):
    """Test running a job."""
    job_id = uuid4()
    job = JobDefinition(
        id=job_id,
        client_id=uuid4(),
        name="Test Job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(entity=ExportEntity.BILL, fields=["id"]),
    )

    job_run = JobRun(
        id=uuid4(),
        job_id=job_id,
        status=JobStatus.PENDING,
    )

    # Mock repository responses
    mock_job_repository.get_by_id = AsyncMock(return_value=job)
    mock_job_run_repository.create = AsyncMock(return_value=job_run)
    mock_message_queue.send_message = AsyncMock(return_value="message-id")

    # Execute
    result = await job_service.run_job(job_id)

    # Verify
    assert result.id == job_run.id
    assert result.status == JobStatus.PENDING
    mock_job_repository.get_by_id.assert_called_once_with(job_id)
    mock_job_run_repository.create.assert_called_once()
    mock_message_queue.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_run_job_no_queue(
    job_service, mock_job_repository, mock_job_run_repository, mock_job_runner
):
    """Test running a job when message queue is not configured."""
    # Create service without message queue
    job_service_no_queue = JobService(
        job_repository=mock_job_repository,
        job_run_repository=mock_job_run_repository,
        scheduler_service=AsyncMock(),
        job_runner=mock_job_runner,
        message_queue=None,  # No queue
    )

    job_id = uuid4()
    job = JobDefinition(
        id=job_id,
        client_id=uuid4(),
        name="Test Job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(entity=ExportEntity.BILL, fields=["id"]),
    )

    job_run = JobRun(
        id=uuid4(),
        job_id=job_id,
        status=JobStatus.PENDING,
    )

    # Mock repository responses
    mock_job_repository.get_by_id = AsyncMock(return_value=job)
    mock_job_run_repository.create = AsyncMock(return_value=job_run)
    mock_job_runner.queue_job_run = AsyncMock()

    # Execute
    result = await job_service_no_queue.run_job(job_id)

    # Verify
    assert result.id == job_run.id
    mock_job_runner.queue_job_run.assert_called_once()


@pytest.mark.asyncio
async def test_get_job_runs(job_service, mock_job_repository, mock_job_run_repository):
    """Test getting job runs."""
    job_id = uuid4()
    job = JobDefinition(
        id=job_id,
        client_id=uuid4(),
        name="Test Job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(entity=ExportEntity.BILL, fields=["id"]),
    )

    runs = [
        JobRun(id=uuid4(), job_id=job_id, status=JobStatus.PENDING),
        JobRun(id=uuid4(), job_id=job_id, status=JobStatus.RUNNING),
    ]

    # Mock repository responses
    mock_job_repository.get_by_id = AsyncMock(return_value=job)
    mock_job_run_repository.get_by_job_id = AsyncMock(return_value=runs)

    # Execute
    result = await job_service.get_job_runs(job_id)

    # Verify
    assert len(result) == 2
    assert all(run.job_id == job_id for run in result)
    # Verify repositories were called
    mock_job_run_repository.get_by_job_id.assert_called_once_with(job_id)
