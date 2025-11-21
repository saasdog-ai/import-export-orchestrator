"""Unit tests for repositories with mocked database."""

from datetime import UTC, datetime
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
from app.infrastructure.db.models import JobDefinitionModel, JobRunModel
from app.infrastructure.db.repositories import JobRepository, JobRunRepository


@pytest.fixture
def mock_db():
    """Create a mocked database."""
    db = MagicMock()
    db.async_session_maker = MagicMock()
    return db


@pytest.fixture
def mock_session():
    """Create a mocked database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_create_job(mock_db, mock_session):
    """Test creating a job with mocked database."""

    # Setup
    test_job = JobDefinition(
        id=uuid4(),
        client_id=uuid4(),
        name="Test Job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(
            entity=ExportEntity.BILL,
            fields=["id", "amount"],
        ),
    )

    # Mock the database model with all required fields
    db_model = JobDefinitionModel(
        id=test_job.id,
        client_id=test_job.client_id,
        name=test_job.name,
        job_type=test_job.job_type.value,
        enabled=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_model.export_config = {"entity": "bill", "fields": ["id", "amount"]}

    # Mock transaction context manager (used by create method)
    mock_db.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_db.transaction.return_value.__aexit__ = AsyncMock(return_value=None)

    # Mock session.refresh to update the model
    async def mock_refresh(obj):
        # Simulate refresh by updating the model
        pass

    mock_session.refresh = AsyncMock(side_effect=mock_refresh)

    # Execute
    repository = JobRepository(mock_db)
    # Mock the _model_to_entity method to return the test_job
    repository._model_to_entity = MagicMock(return_value=test_job)
    created_job = await repository.create(test_job)

    # Verify
    assert created_job.id == test_job.id
    assert created_job.name == test_job.name
    mock_session.add.assert_called_once()


@pytest.mark.asyncio
async def test_get_job_by_id(mock_db, mock_session):
    """Test getting a job by ID with mocked database."""

    job_id = uuid4()
    client_id = uuid4()
    db_model = JobDefinitionModel(
        id=job_id,
        client_id=client_id,
        name="Test Job",
        job_type=JobType.EXPORT.value,
        enabled=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    # Set export_config as JSON
    db_model.export_config = {
        "entity": "bill",
        "fields": ["id", "amount"],
    }

    # Mock session context manager
    mock_db.async_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_db.async_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)

    # Mock session.execute
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = db_model
    mock_session.execute.return_value = result_mock

    # Execute
    repository = JobRepository(mock_db)
    retrieved_job = await repository.get_by_id(job_id)

    # Verify
    assert retrieved_job is not None
    assert retrieved_job.id == job_id
    assert retrieved_job.name == "Test Job"


@pytest.mark.asyncio
async def test_get_jobs_by_client(mock_db, mock_session):
    """Test getting jobs by client ID with mocked database."""

    client_id = uuid4()
    db_models = [
        JobDefinitionModel(
            id=uuid4(),
            client_id=client_id,
            name="Job 1",
            job_type=JobType.EXPORT.value,
            enabled=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
        JobDefinitionModel(
            id=uuid4(),
            client_id=client_id,
            name="Job 2",
            job_type=JobType.EXPORT.value,
            enabled=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
    ]
    # Set export_config for both models
    for model in db_models:
        model.export_config = {"entity": "bill", "fields": ["id"]}

    # Mock session context manager
    mock_db.async_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_db.async_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)

    # Mock session.execute
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = db_models
    mock_session.execute.return_value = result_mock

    # Execute
    repository = JobRepository(mock_db)
    jobs = await repository.get_by_client_id(client_id)

    # Verify
    assert len(jobs) == 2
    assert all(job.client_id == client_id for job in jobs)


@pytest.mark.asyncio
async def test_create_job_run(mock_db, mock_session):
    """Test creating a job run with mocked database."""

    job_id = uuid4()
    job_run = JobRun(
        job_id=job_id,
        status=JobStatus.PENDING,
    )

    db_model = JobRunModel(
        id=job_run.id,
        job_id=job_id,
        status=JobStatus.PENDING.value,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    # Mock transaction context manager (used by create method)
    mock_db.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_db.transaction.return_value.__aexit__ = AsyncMock(return_value=None)

    # Mock session.refresh to update the model
    async def mock_refresh(obj):
        # Simulate refresh by updating the model
        pass

    mock_session.refresh = AsyncMock(side_effect=mock_refresh)

    # Execute
    repository = JobRunRepository(mock_db)
    # Mock the _model_to_entity method to return the job_run
    repository._model_to_entity = MagicMock(return_value=job_run)
    created_run = await repository.create(job_run)

    # Verify
    assert created_run.id == job_run.id
    assert created_run.status == JobStatus.PENDING
    mock_session.add.assert_called_once()


@pytest.mark.asyncio
async def test_update_job_run_status(mock_db, mock_session):
    """Test updating job run status with mocked database."""

    run_id = uuid4()
    job_id = uuid4()
    started_at = datetime.now(UTC)

    db_model = JobRunModel(
        id=run_id,
        job_id=job_id,
        status=JobStatus.RUNNING.value,
        started_at=started_at,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    # Mock transaction context manager (used by update_status method)
    mock_db.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_db.transaction.return_value.__aexit__ = AsyncMock(return_value=None)

    # Mock session.execute - first call is update, second call is select
    result_mock_update = MagicMock()
    result_mock_select = MagicMock()
    result_mock_select.scalar_one.return_value = db_model
    # First call is update (no return needed), second call is select
    mock_session.execute = AsyncMock(side_effect=[result_mock_update, result_mock_select])
    mock_session.flush = AsyncMock()

    # Execute
    repository = JobRunRepository(mock_db)
    updated_run = await repository.update_status(
        run_id,
        JobStatus.RUNNING,
        started_at=started_at,
    )

    # Verify
    assert updated_run.status == JobStatus.RUNNING
    assert updated_run.started_at is not None
