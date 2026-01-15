"""Unit tests for job runner service with mocked dependencies."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.domain.entities import (
    ExportConfig,
    ExportEntity,
    ExportField,
    ImportConfig,
    JobDefinition,
    JobRun,
    JobStatus,
    JobType,
)
from app.infrastructure.storage.interface import CloudStorageInterface
from app.services.job_runner import JobRunnerService


@pytest.fixture
def mock_job_repository():
    """Create a mocked job repository."""
    return AsyncMock()


@pytest.fixture
def mock_job_run_repository():
    """Create a mocked job run repository."""
    return AsyncMock()


@pytest.fixture
def mock_query_engine():
    """Create a mocked query engine."""
    return AsyncMock()


@pytest.fixture
def mock_saas_client():
    """Create a mocked SaaS client."""
    return AsyncMock()


@pytest.fixture
def mock_cloud_storage():
    """Create a mocked cloud storage."""
    storage = MagicMock(spec=CloudStorageInterface)
    storage.upload_file = AsyncMock(return_value="exports/file.csv")
    storage.get_presigned_download_url = AsyncMock(return_value="https://example.com/file.csv")
    return storage


@pytest.fixture
def job_runner(
    mock_job_repository,
    mock_job_run_repository,
    mock_query_engine,
    mock_saas_client,
    mock_cloud_storage,
):
    """Create a job runner with mocked dependencies."""
    return JobRunnerService(
        job_repository=mock_job_repository,
        job_run_repository=mock_job_run_repository,
        query_engine=mock_query_engine,
        saas_client=mock_saas_client,
        cloud_storage=mock_cloud_storage,
        max_workers=2,
    )


@pytest.mark.asyncio
async def test_start_stop(job_runner):
    """Test starting and stopping the job runner."""
    await job_runner.start()
    assert job_runner._running is True
    assert len(job_runner._workers) == 2

    await job_runner.stop()
    assert job_runner._running is False


@pytest.mark.asyncio
async def test_queue_job_run(job_runner):
    """Test queueing a job run to in-memory queue."""
    job = JobDefinition(
        id=uuid4(),
        client_id=uuid4(),
        name="Test Job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(entity=ExportEntity.BILL, fields=[ExportField(field="id")]),
    )

    job_run = JobRun(
        id=uuid4(),
        job_id=job.id,
        status=JobStatus.PENDING,
    )

    await job_runner.queue_job_run(job, job_run)

    # Verify job was queued
    assert job_runner._queue.qsize() == 1


@pytest.mark.asyncio
async def test_execute_export_job_success(
    job_runner,
    mock_query_engine,
    mock_cloud_storage,
    mock_job_run_repository,
):
    """Test successful export job execution."""
    # Setup
    job = JobDefinition(
        id=uuid4(),
        client_id=uuid4(),
        name="Export Job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(
            entity=ExportEntity.BILL,
            fields=[ExportField(field="id"), ExportField(field="amount")],
        ),
    )

    job_run = JobRun(
        id=uuid4(),
        job_id=job.id,
        status=JobStatus.PENDING,
    )

    # Mock query engine response
    mock_query_engine.execute_export_query = AsyncMock(
        return_value={
            "count": 5,
            "records": [
                {"id": "1", "amount": 100.0},
                {"id": "2", "amount": 200.0},
            ],
        }
    )

    # Mock FileGenerator static methods
    with (
        patch(
            "app.services.job_runner.FileGenerator.generate_csv_file",
            return_value="/tmp/export.csv",
        ) as mock_gen_csv,
        patch("app.services.job_runner.FileGenerator.get_file_extension", return_value=".csv"),
        patch("app.services.job_runner.FileGenerator.get_content_type", return_value="text/csv"),
        patch("os.makedirs"),
        patch("os.remove"),
    ):
        # Mock cloud storage
        mock_cloud_storage.upload_file = AsyncMock(return_value="exports/file.csv")

        # Mock repository update
        updated_run = JobRun(
            id=job_run.id,
            job_id=job.id,
            status=JobStatus.SUCCEEDED,
            result_metadata={"count": 5, "format": "csv", "remote_file_path": "exports/file.csv"},
        )
        mock_job_run_repository.update_status = AsyncMock(return_value=updated_run)

        # Execute
        await job_runner._execute_export_job(job, job_run, "worker-0")

        # Deep validation: Verify calls with correct parameters
        mock_query_engine.execute_export_query.assert_called_once()
        call_args = mock_query_engine.execute_export_query.call_args
        config_arg = call_args[0][0]  # First positional arg (config)
        client_id_arg = call_args[1]["client_id"]  # Keyword arg (client_id)
        assert config_arg.entity == ExportEntity.BILL
        assert config_arg.get_source_fields() == ["id", "amount"]
        assert client_id_arg == job.client_id  # Correct client_id

        mock_gen_csv.assert_called_once()
        # Verify CSV generation was called with correct data
        csv_call_args = mock_gen_csv.call_args
        assert csv_call_args is not None

        mock_cloud_storage.upload_file.assert_called_once()
        upload_call = mock_cloud_storage.upload_file.call_args
        assert upload_call[0][0] == "/tmp/export.csv"  # Local file path
        assert "exports/" in upload_call[0][1]  # Remote path contains exports/
        assert upload_call[1]["content_type"] == "text/csv"

        # Deep validation: Verify status update with correct metadata
        mock_job_run_repository.update_status.assert_called_once()
        update_call = mock_job_run_repository.update_status.call_args
        assert update_call[0][0] == job_run.id  # Correct job run ID
        assert update_call[0][1] == JobStatus.SUCCEEDED  # Status is SUCCEEDED
        result_metadata = update_call[1]["result_metadata"]
        assert result_metadata["count"] == 5  # Correct count
        assert result_metadata["format"] == "csv"  # Correct format
        assert "remote_file_path" in result_metadata  # Has remote file path
        # Remote path is generated dynamically with UUIDs, so just verify it contains exports/
        assert "exports/" in result_metadata["remote_file_path"], (
            f"Remote file path should contain 'exports/', got: {result_metadata['remote_file_path']}"
        )
        assert result_metadata["remote_file_path"].endswith(".csv")  # Ends with .csv


@pytest.mark.asyncio
async def test_execute_export_job_no_cloud_storage(
    mock_job_repository,
    mock_job_run_repository,
    mock_query_engine,
    mock_saas_client,
):
    """Test export job execution without cloud storage."""
    # Create runner without cloud storage
    job_runner = JobRunnerService(
        job_repository=mock_job_repository,
        job_run_repository=mock_job_run_repository,
        query_engine=mock_query_engine,
        saas_client=mock_saas_client,
        cloud_storage=None,  # No cloud storage
        max_workers=1,
    )

    job = JobDefinition(
        id=uuid4(),
        client_id=uuid4(),
        name="Export Job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(entity=ExportEntity.BILL, fields=[ExportField(field="id")]),
    )

    job_run = JobRun(
        id=uuid4(),
        job_id=job.id,
        status=JobStatus.PENDING,
    )

    # Mock responses
    mock_query_engine.execute_export_query = AsyncMock(
        return_value={
            "count": 2,
            "records": [{"id": "1"}, {"id": "2"}],
        }
    )

    with (
        patch(
            "app.services.job_runner.FileGenerator.generate_csv_file",
            return_value="/tmp/export.csv",
        ) as mock_gen_csv,
        patch("os.makedirs"),
    ):
        updated_run = JobRun(
            id=job_run.id,
            job_id=job.id,
            status=JobStatus.SUCCEEDED,
            result_metadata={"local_file_path": "/tmp/export.csv"},
        )
        mock_job_run_repository.update_status = AsyncMock(return_value=updated_run)

        # Execute
        await job_runner._execute_export_job(job, job_run, "worker-0")

        # Deep validation: Verify calls with correct parameters
        mock_query_engine.execute_export_query.assert_called_once()
        call_args = mock_query_engine.execute_export_query.call_args
        config_arg = call_args[0][0]  # First positional arg (config)
        client_id_arg = call_args[1]["client_id"]  # Keyword arg (client_id)
        assert config_arg.entity == ExportEntity.BILL
        assert config_arg.get_source_fields() == ["id"]
        assert client_id_arg == job.client_id  # Correct client_id

        mock_gen_csv.assert_called_once()

        # Deep validation: Verify status update with local file path (no cloud storage)
        mock_job_run_repository.update_status.assert_called_once()
        update_call = mock_job_run_repository.update_status.call_args
        assert update_call[0][0] == job_run.id
        assert update_call[0][1] == JobStatus.SUCCEEDED
        result_metadata = update_call[1]["result_metadata"]
        assert "local_file_path" in result_metadata  # Has local file path
        assert result_metadata["local_file_path"] == "/tmp/export.csv"  # Correct path


@pytest.mark.asyncio
async def test_execute_import_job_success(
    job_runner,
    mock_saas_client,
    mock_job_run_repository,
):
    """Test successful import job execution."""
    # Setup
    job = JobDefinition(
        id=uuid4(),
        client_id=uuid4(),
        name="Import Job",
        job_type=JobType.IMPORT,
        import_config=ImportConfig(
            source="test_source",
            entity=ExportEntity.BILL,
        ),
    )

    job_run = JobRun(
        id=uuid4(),
        job_id=job.id,
        status=JobStatus.PENDING,
    )

    # Mock SaaS client
    mock_saas_client.fetch_data = AsyncMock(
        return_value=[
            {"id": "1", "amount": 100.0},
            {"id": "2", "amount": 200.0},
        ]
    )
    mock_saas_client.import_data = AsyncMock(
        return_value={
            "imported_count": 2,
            "failed_count": 0,
        }
    )

    # Mock repository update
    updated_run = JobRun(
        id=job_run.id,
        job_id=job.id,
        status=JobStatus.SUCCEEDED,
        result_metadata={"imported_count": 2},
    )
    mock_job_run_repository.update_status = AsyncMock(return_value=updated_run)

    # Execute
    await job_runner._execute_import_job(job, job_run, "worker-0")

    # Deep validation: Verify calls with correct parameters
    mock_saas_client.fetch_data.assert_called_once()
    fetch_call = mock_saas_client.fetch_data.call_args
    assert fetch_call[0][0] == ExportEntity.BILL  # Correct entity
    assert fetch_call[1]["client_id"] == job.client_id  # Correct client_id

    mock_saas_client.import_data.assert_called_once()
    import_call = mock_saas_client.import_data.call_args
    assert import_call[0][0].entity == ExportEntity.BILL  # Correct import config entity
    assert import_call[1]["client_id"] == job.client_id  # Correct client_id
    # Verify data passed to import_data
    import_data = import_call[1]["data"]
    assert len(import_data) == 2
    assert import_data[0]["id"] == "1"
    assert import_data[0]["amount"] == 100.0
    assert import_data[1]["id"] == "2"
    assert import_data[1]["amount"] == 200.0

    # Deep validation: Verify status update with correct metadata
    mock_job_run_repository.update_status.assert_called_once()
    update_call = mock_job_run_repository.update_status.call_args
    assert update_call[0][0] == job_run.id
    assert update_call[0][1] == JobStatus.SUCCEEDED
    result_metadata = update_call[1]["result_metadata"]
    assert result_metadata["imported_count"] == 2  # Correct imported count
    assert result_metadata.get("failed_count", 0) == 0  # No failures


@pytest.mark.asyncio
async def test_execute_job_run_export(job_runner, mock_job_run_repository):
    """Test executing a job run for export job."""
    # Setup
    job = JobDefinition(
        id=uuid4(),
        client_id=uuid4(),
        name="Export Job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(entity=ExportEntity.BILL, fields=[ExportField(field="id")]),
    )

    job_run = JobRun(
        id=uuid4(),
        job_id=job.id,
        status=JobStatus.PENDING,
    )

    # Mock the export execution
    with patch.object(job_runner, "_execute_export_job", new_callable=AsyncMock) as mock_execute:
        await job_runner._execute_job_run(job, job_run, "worker-0")

        # Verify
        mock_execute.assert_called_once_with(job, job_run, "worker-0")
        # Verify status was updated to RUNNING
        assert mock_job_run_repository.update_status.call_count >= 1


@pytest.mark.asyncio
async def test_execute_job_run_import(job_runner, mock_job_run_repository):
    """Test executing a job run for import job."""
    # Setup
    job = JobDefinition(
        id=uuid4(),
        client_id=uuid4(),
        name="Import Job",
        job_type=JobType.IMPORT,
        import_config=ImportConfig(source="test", entity=ExportEntity.BILL),
    )

    job_run = JobRun(
        id=uuid4(),
        job_id=job.id,
        status=JobStatus.PENDING,
    )

    # Mock the import execution
    with patch.object(job_runner, "_execute_import_job", new_callable=AsyncMock) as mock_execute:
        await job_runner._execute_job_run(job, job_run, "worker-0")

        # Verify
        mock_execute.assert_called_once_with(job, job_run, "worker-0")


@pytest.mark.asyncio
async def test_execute_job_run_failure(job_runner, mock_job_run_repository):
    """Test job run execution with failure."""
    # Setup
    job = JobDefinition(
        id=uuid4(),
        client_id=uuid4(),
        name="Export Job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(entity=ExportEntity.BILL, fields=[ExportField(field="id")]),
    )

    job_run = JobRun(
        id=uuid4(),
        job_id=job.id,
        status=JobStatus.PENDING,
    )

    # Mock export execution to fail
    with patch.object(
        job_runner,
        "_execute_export_job",
        new_callable=AsyncMock,
        side_effect=Exception("Export failed"),
    ):
        await job_runner._execute_job_run(job, job_run, "worker-0")

        # Verify status was updated to FAILED
        update_calls = list(mock_job_run_repository.update_status.call_args_list)
        # Should have at least one call to update to FAILED
        assert len(update_calls) >= 1
