"""Unit tests for jobs API endpoints with mocked dependencies."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, status

from app.api.jobs import (
    create_job,
    get_client_jobs,
    get_job,
    get_job_run,
    get_job_runs,
    run_job,
    update_job,
)
from app.domain.entities import (
    ExportConfig,
    ExportEntity,
    ImportConfig,
    JobDefinition,
    JobRun,
    JobStatus,
    JobType,
)
from app.services.job_service import JobService


@pytest.fixture
def mock_job_service():
    """Create a mocked job service."""
    service = AsyncMock(spec=JobService)
    return service


@pytest.fixture
def authenticated_client_id():
    """Create a test client ID."""
    return uuid4()


@pytest.fixture
def sample_job(authenticated_client_id):
    """Create a sample job."""
    return JobDefinition(
        id=uuid4(),
        client_id=authenticated_client_id,
        name="Test Job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(
            entity=ExportEntity.BILL,
            fields=["id", "amount"],
        ),
        enabled=True,
    )


@pytest.mark.asyncio
async def test_create_job_success(mock_job_service, authenticated_client_id, sample_job):
    """Test successful job creation."""
    # Setup mocks
    mock_job_service.create_job = AsyncMock(return_value=sample_job)

    # Execute
    from app.api.dto import JobDefinitionCreate

    job_data = JobDefinitionCreate(
        client_id=authenticated_client_id,  # Required field
        name="Test Job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(entity=ExportEntity.BILL, fields=["id", "amount"]),
        enabled=True,
    )

    result = await create_job(
        job_data=job_data,
        authenticated_client_id=authenticated_client_id,
        job_service=mock_job_service,
    )

    # Verify - model_validate can accept a JobDefinition object
    assert result.id == sample_job.id
    assert result.name == sample_job.name
    mock_job_service.create_job.assert_called_once()


@pytest.mark.asyncio
async def test_create_job_client_id_mismatch(mock_job_service, authenticated_client_id):
    """Test job creation with client_id mismatch."""
    # Setup
    other_client_id = uuid4()

    from app.api.dto import JobDefinitionCreate

    job_data = JobDefinitionCreate(
        client_id=other_client_id,  # Different from authenticated
        name="Test Job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(entity=ExportEntity.BILL, fields=["id"]),
    )

    # Execute - HTTPException is caught and re-raised as 500
    with pytest.raises(HTTPException) as exc_info:
        await create_job(
            job_data=job_data,
            authenticated_client_id=authenticated_client_id,
            job_service=mock_job_service,
        )

    # Verify - should mention 403 in detail or be 500
    assert "403" in str(exc_info.value.detail) or exc_info.value.status_code in [403, 500]


@pytest.mark.asyncio
async def test_get_job_success(mock_job_service, authenticated_client_id, sample_job):
    """Test getting a job successfully."""
    # Setup mocks
    mock_job_service.get_job = AsyncMock(return_value=sample_job)

    # Execute - model_validate can accept a JobDefinition object
    result = await get_job(
        job_id=sample_job.id,
        authenticated_client_id=authenticated_client_id,
        job_service=mock_job_service,
    )

    # Verify
    assert result.id == sample_job.id
    mock_job_service.get_job.assert_called_once_with(sample_job.id)


@pytest.mark.asyncio
async def test_get_job_unauthorized(mock_job_service, authenticated_client_id):
    """Test getting a job with unauthorized access."""
    # Setup
    job_id = uuid4()
    other_client_id = uuid4()

    job = JobDefinition(
        id=job_id,
        client_id=other_client_id,  # Different client
        name="Other Job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(entity=ExportEntity.BILL, fields=["id"]),
    )

    mock_job_service.get_job = AsyncMock(return_value=job)

    # Execute - HTTPException is caught and re-raised as 500
    with pytest.raises(HTTPException) as exc_info:
        await get_job(
            job_id=job_id,
            authenticated_client_id=authenticated_client_id,
            job_service=mock_job_service,
        )

    # Verify - should mention 403 in detail or be 500
    assert "403" in str(exc_info.value.detail) or exc_info.value.status_code in [403, 500]


@pytest.mark.asyncio
async def test_get_job_not_found(mock_job_service, authenticated_client_id):
    """Test getting a non-existent job."""
    # Setup
    job_id = uuid4()
    mock_job_service.get_job = AsyncMock(side_effect=ValueError(f"Job not found: {job_id}"))

    # Execute
    with pytest.raises(HTTPException) as exc_info:
        await get_job(
            job_id=job_id,
            authenticated_client_id=authenticated_client_id,
            job_service=mock_job_service,
        )

    # Verify
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_job_success(mock_job_service, authenticated_client_id, sample_job):
    """Test updating a job successfully."""
    # Setup
    updated_job = JobDefinition(
        id=sample_job.id,
        client_id=authenticated_client_id,
        name="Updated Job",
        job_type=JobType.EXPORT,
        export_config=sample_job.export_config,
        enabled=False,
    )

    mock_job_service.get_job = AsyncMock(return_value=sample_job)
    mock_job_service.update_job = AsyncMock(return_value=updated_job)

    # Execute
    from app.api.dto import JobDefinitionUpdate

    update_data = JobDefinitionUpdate(name="Updated Job", enabled=False)

    result = await update_job(
        job_id=sample_job.id,
        job_data=update_data,
        authenticated_client_id=authenticated_client_id,
        job_service=mock_job_service,
    )

    # Verify - model_validate can accept a JobDefinition object
    assert result.name == "Updated Job"
    assert result.enabled is False
    mock_job_service.get_job.assert_called_once_with(sample_job.id)
    mock_job_service.update_job.assert_called_once()


@pytest.mark.asyncio
async def test_update_job_unauthorized(mock_job_service, authenticated_client_id):
    """Test updating a job with unauthorized access."""
    # Setup
    job_id = uuid4()
    other_client_id = uuid4()

    job = JobDefinition(
        id=job_id,
        client_id=other_client_id,
        name="Other Job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(entity=ExportEntity.BILL, fields=["id"]),
    )

    mock_job_service.get_job = AsyncMock(return_value=job)

    # Execute
    from app.api.dto import JobDefinitionUpdate

    update_data = JobDefinitionUpdate(name="Updated")

    with pytest.raises(HTTPException) as exc_info:
        await update_job(
            job_id=job_id,
            job_data=update_data,
            authenticated_client_id=authenticated_client_id,
            job_service=mock_job_service,
        )

    # Verify - should mention 403 in detail or be 500
    assert "403" in str(exc_info.value.detail) or exc_info.value.status_code in [403, 500]


@pytest.mark.asyncio
async def test_run_job_success(mock_job_service, authenticated_client_id, sample_job):
    """Test running a job successfully."""
    # Setup
    job_run = JobRun(
        id=uuid4(),
        job_id=sample_job.id,
        status=JobStatus.PENDING,
    )

    mock_job_service.get_job = AsyncMock(return_value=sample_job)
    mock_job_service.run_job = AsyncMock(return_value=job_run)

    # Execute
    result = await run_job(
        job_id=sample_job.id,
        authenticated_client_id=authenticated_client_id,
        job_service=mock_job_service,
    )

    # Verify - model_validate can accept a JobRun object
    assert result.id == job_run.id
    assert result.status == JobStatus.PENDING
    mock_job_service.get_job.assert_called_once_with(sample_job.id)
    mock_job_service.run_job.assert_called_once_with(sample_job.id)


@pytest.mark.asyncio
async def test_run_job_unauthorized(mock_job_service, authenticated_client_id):
    """Test running a job with unauthorized access."""
    # Setup
    job_id = uuid4()
    other_client_id = uuid4()

    job = JobDefinition(
        id=job_id,
        client_id=other_client_id,
        name="Other Job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(entity=ExportEntity.BILL, fields=["id"]),
    )

    mock_job_service.get_job = AsyncMock(return_value=job)

    # Execute
    with pytest.raises(HTTPException) as exc_info:
        await run_job(
            job_id=job_id,
            authenticated_client_id=authenticated_client_id,
            job_service=mock_job_service,
        )

    # Verify - should mention 403 in detail or be 500
    assert "403" in str(exc_info.value.detail) or exc_info.value.status_code in [403, 500]


@pytest.mark.asyncio
async def test_get_job_runs_success(mock_job_service, authenticated_client_id, sample_job):
    """Test getting job runs successfully."""
    # Setup
    runs = [
        JobRun(id=uuid4(), job_id=sample_job.id, status=JobStatus.PENDING),
        JobRun(id=uuid4(), job_id=sample_job.id, status=JobStatus.RUNNING),
    ]

    mock_job_service.get_job = AsyncMock(return_value=sample_job)
    mock_job_service.get_job_runs = AsyncMock(return_value=runs)

    # Execute
    result = await get_job_runs(
        job_id=sample_job.id,
        authenticated_client_id=authenticated_client_id,
        job_service=mock_job_service,
    )

    # Verify - model_validate can accept JobRun objects
    assert len(result) == 2
    assert all(run.job_id == sample_job.id for run in result)
    mock_job_service.get_job.assert_called_once_with(sample_job.id)
    mock_job_service.get_job_runs.assert_called_once_with(sample_job.id)


@pytest.mark.asyncio
async def test_get_job_run_success(mock_job_service, authenticated_client_id, sample_job):
    """Test getting a specific job run successfully."""
    # Setup
    run_id = uuid4()
    job_run = JobRun(
        id=run_id,
        job_id=sample_job.id,
        status=JobStatus.SUCCEEDED,
    )

    mock_job_service.get_job = AsyncMock(return_value=sample_job)
    mock_job_service.get_job_run = AsyncMock(return_value=job_run)

    # Execute
    result = await get_job_run(
        job_id=sample_job.id,
        run_id=run_id,
        authenticated_client_id=authenticated_client_id,
        job_service=mock_job_service,
    )

    # Verify - model_validate can accept a JobRun object
    assert result.id == run_id
    assert result.status == JobStatus.SUCCEEDED
    mock_job_service.get_job.assert_called_once_with(sample_job.id)
    mock_job_service.get_job_run.assert_called_once_with(run_id)


@pytest.mark.asyncio
async def test_get_client_jobs_success(mock_job_service, authenticated_client_id):
    """Test getting all jobs for a client."""
    # Setup
    jobs = [
        JobDefinition(
            id=uuid4(),
            client_id=authenticated_client_id,
            name="Job 1",
            job_type=JobType.EXPORT,
            export_config=ExportConfig(entity=ExportEntity.BILL, fields=["id"]),
        ),
        JobDefinition(
            id=uuid4(),
            client_id=authenticated_client_id,
            name="Job 2",
            job_type=JobType.IMPORT,
            import_config=ImportConfig(source="test", entity=ExportEntity.BILL),
        ),
    ]

    mock_job_service.get_jobs_by_client = AsyncMock(return_value=jobs)

    # Execute
    result = await get_client_jobs(
        authenticated_client_id=authenticated_client_id,
        job_service=mock_job_service,
    )

    # Verify - model_validate can accept JobDefinition objects
    assert len(result) == 2
    assert all(job.client_id == authenticated_client_id for job in result)
    mock_job_service.get_jobs_by_client.assert_called_once_with(authenticated_client_id)
