"""Unit tests for imports API endpoints."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.api.imports import ExecuteImportRequest, execute_import, upload_import_file
from app.domain.entities import ExportEntity, JobDefinition, JobRun, JobStatus, JobType
from app.infrastructure.storage.interface import CloudStorageInterface
from app.services.job_service import JobService


@pytest.fixture
def mock_upload_file():
    """Create a mock UploadFile."""
    file = MagicMock()
    file.filename = "test_bills.csv"
    file.content_type = "text/csv"
    file.read = AsyncMock(return_value=b"id,amount,date\n,100.00,2024-01-01\n")
    return file


@pytest.fixture
def mock_cloud_storage():
    """Create a mock cloud storage."""
    storage = MagicMock(spec=CloudStorageInterface)
    storage.upload_file = AsyncMock(return_value="imports/test/temp/test_bills.csv")
    return storage


@pytest.fixture
def mock_job_service():
    """Create a mock job service."""
    service = MagicMock(spec=JobService)
    from app.domain.entities import ImportConfig

    import_config = ImportConfig(
        source="cloud_storage",
        entity=ExportEntity.BILL,
        options={"source_file": "test.csv"},
    )
    job = JobDefinition(
        id=uuid4(),
        client_id=uuid4(),
        name="Test Import",
        job_type=JobType.IMPORT,
        import_config=import_config,
        enabled=True,
    )
    job_run = JobRun(
        id=uuid4(),
        job_id=job.id,
        status=JobStatus.PENDING,
    )
    service.create_job = AsyncMock(return_value=job)
    service.run_job = AsyncMock(return_value=job_run)
    return service


@pytest.fixture
def test_client_id():
    """Create a test client ID."""
    return uuid4()


@pytest.mark.asyncio
async def test_upload_import_file_success(
    mock_upload_file, mock_cloud_storage, test_client_id, tmp_path
):
    """Test successful file upload and validation."""
    temp_file = tmp_path / f"import_{test_client_id}_test_bills.csv"
    temp_file.write_bytes(b"id,amount,date\n,100.00,2024-01-01\n")

    with (
        patch("app.api.imports.settings") as mock_settings,
        patch("app.api.imports.ImportValidator") as mock_validator,
        patch("app.api.imports.os.path.join", return_value=str(temp_file)),
        patch("app.api.imports.os.makedirs"),
        patch("app.api.imports.os.remove"),
    ):
        mock_settings.export_local_path = str(tmp_path)
        mock_validator.validate_file_format.return_value = (True, None)
        mock_validator.validate_import_file = AsyncMock(return_value=(True, []))

        response = await upload_import_file(
            file=mock_upload_file,
            entity=ExportEntity.BILL,
            authenticated_client_id=test_client_id,
            cloud_storage=mock_cloud_storage,
        )

        assert response.status_code == 200
        content = json.loads(response.body.decode()) if hasattr(response, "body") else response
        assert "validated" in str(content).lower() or "validated" in str(response)


@pytest.mark.asyncio
async def test_upload_import_file_validation_failed(
    mock_upload_file, mock_cloud_storage, test_client_id, tmp_path
):
    """Test file upload with validation failure."""
    temp_file = tmp_path / f"import_{test_client_id}_test_bills.csv"
    temp_file.write_bytes(b"invalid content")

    with (
        patch("app.api.imports.settings") as mock_settings,
        patch("app.api.imports.ImportValidator") as mock_validator,
        patch("app.api.imports.os.path.join", return_value=str(temp_file)),
        patch("app.api.imports.os.makedirs"),
        patch("app.api.imports.os.remove"),
    ):
        mock_settings.export_local_path = str(tmp_path)
        mock_validator.validate_file_format.return_value = (False, "Invalid file format")

        response = await upload_import_file(
            file=mock_upload_file,
            entity=ExportEntity.BILL,
            authenticated_client_id=test_client_id,
            cloud_storage=mock_cloud_storage,
        )

        assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_import_file_no_cloud_storage(mock_upload_file, test_client_id, tmp_path):
    """Test file upload without cloud storage."""
    temp_file = tmp_path / f"import_{test_client_id}_test_bills.csv"
    temp_file.write_bytes(b"id,amount,date\n,100.00,2024-01-01\n")

    with (
        patch("app.api.imports.settings") as mock_settings,
        patch("app.api.imports.ImportValidator") as mock_validator,
        patch("app.api.imports.os.path.join", return_value=str(temp_file)),
        patch("app.api.imports.os.makedirs"),
    ):
        mock_settings.export_local_path = str(tmp_path)
        mock_validator.validate_file_format.return_value = (True, None)
        mock_validator.validate_import_file = AsyncMock(return_value=(True, []))

        response = await upload_import_file(
            file=mock_upload_file,
            entity=ExportEntity.BILL,
            authenticated_client_id=test_client_id,
            cloud_storage=None,
        )

        assert response.status_code == 200


@pytest.mark.asyncio
async def test_execute_import_success(mock_job_service, test_client_id):
    """Test successful import execution."""
    request = ExecuteImportRequest(
        file_path="imports/test/temp/test_bills.csv",
        entity=ExportEntity.BILL,
    )

    response = await execute_import(
        request=request,
        authenticated_client_id=test_client_id,
        job_service=mock_job_service,
    )

    assert response.status_code == 201
    mock_job_service.create_job.assert_called_once()
    mock_job_service.run_job.assert_called_once()


@pytest.mark.asyncio
async def test_execute_import_value_error(mock_job_service, test_client_id):
    """Test import execution with ValueError."""
    request = ExecuteImportRequest(
        file_path="imports/test/temp/test_bills.csv",
        entity=ExportEntity.BILL,
    )

    mock_job_service.create_job = AsyncMock(side_effect=ValueError("Invalid job"))

    with pytest.raises(Exception):  # HTTPException
        await execute_import(
            request=request,
            authenticated_client_id=test_client_id,
            job_service=mock_job_service,
        )


@pytest.mark.asyncio
async def test_execute_import_generic_error(mock_job_service, test_client_id):
    """Test import execution with generic error."""
    request = ExecuteImportRequest(
        file_path="imports/test/temp/test_bills.csv",
        entity=ExportEntity.BILL,
    )

    mock_job_service.create_job = AsyncMock(side_effect=Exception("Unexpected error"))

    with pytest.raises(Exception):  # HTTPException
        await execute_import(
            request=request,
            authenticated_client_id=test_client_id,
            job_service=mock_job_service,
        )
