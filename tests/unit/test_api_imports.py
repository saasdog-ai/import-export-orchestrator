"""Unit tests for imports API endpoints."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.dto import ImportConfirmUploadRequest, ImportExecuteRequest, ImportRequestUploadRequest
from app.api.imports import confirm_upload, execute_import, request_upload
from app.domain.entities import ExportEntity, JobDefinition, JobRun, JobStatus, JobType
from app.infrastructure.storage.interface import CloudStorageInterface
from app.services.job_service import JobService


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
async def test_execute_import_success(mock_job_service, test_client_id):
    """Test successful import execution."""
    request = ImportExecuteRequest(
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
    # Verify run_job was called with client_id
    call_args = mock_job_service.run_job.call_args
    assert call_args[1]["client_id"] == test_client_id


@pytest.mark.asyncio
async def test_execute_import_value_error(mock_job_service, test_client_id):
    """Test import execution with ValueError."""
    request = ImportExecuteRequest(
        file_path="imports/test/temp/test_bills.csv",
        entity=ExportEntity.BILL,
    )

    mock_job_service.create_job = AsyncMock(side_effect=ValueError("Invalid job"))

    with pytest.raises(HTTPException):  # HTTPException
        await execute_import(
            request=request,
            authenticated_client_id=test_client_id,
            job_service=mock_job_service,
        )


@pytest.mark.asyncio
async def test_execute_import_generic_error(mock_job_service, test_client_id):
    """Test import execution with generic error.

    Generic exceptions now propagate to the global exception handler
    for secure error message handling (no internal details exposed).
    """
    request = ImportExecuteRequest(
        file_path="imports/test/temp/test_bills.csv",
        entity=ExportEntity.BILL,
    )

    mock_job_service.create_job = AsyncMock(side_effect=Exception("Unexpected error"))

    # Generic exceptions propagate to global handler (not caught locally)
    with pytest.raises(Exception, match="Unexpected error"):
        await execute_import(
            request=request,
            authenticated_client_id=test_client_id,
            job_service=mock_job_service,
        )


# ============================================================================
# Tests for /imports/request-upload
# ============================================================================


@pytest.mark.asyncio
async def test_request_upload_returns_presigned_url(mock_cloud_storage, test_client_id):
    """Test that request-upload returns a presigned URL."""
    mock_cloud_storage.generate_presigned_upload_url = AsyncMock(
        return_value="https://s3.amazonaws.com/bucket/key?Signature=abc"
    )

    request = ImportRequestUploadRequest(
        filename="bills.csv",
        entity=ExportEntity.BILL,
        content_type="text/csv",
    )

    with patch("app.api.imports.settings") as mock_settings:
        mock_settings.presigned_url_expiration = 3600

        response = await request_upload(
            request=request,
            authenticated_client_id=test_client_id,
            cloud_storage=mock_cloud_storage,
        )

    assert response.upload_url == "https://s3.amazonaws.com/bucket/key?Signature=abc"
    assert response.file_key.startswith(f"imports/{test_client_id}/temp/")
    assert response.file_key.endswith("_bills.csv")
    assert response.expires_in == 3600
    mock_cloud_storage.generate_presigned_upload_url.assert_called_once()


@pytest.mark.asyncio
async def test_request_upload_rejects_invalid_content_type(mock_cloud_storage, test_client_id):
    """Test that request-upload rejects unsupported content types."""
    request = ImportRequestUploadRequest(
        filename="bills.xlsx",
        entity=ExportEntity.BILL,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    with pytest.raises(HTTPException) as exc_info:
        await request_upload(
            request=request,
            authenticated_client_id=test_client_id,
            cloud_storage=mock_cloud_storage,
        )

    assert exc_info.value.status_code == 400
    assert "Unsupported content type" in exc_info.value.detail


@pytest.mark.asyncio
async def test_request_upload_rejects_invalid_extension(mock_cloud_storage, test_client_id):
    """Test that request-upload rejects unsupported file extensions."""
    request = ImportRequestUploadRequest(
        filename="bills.xlsx",
        entity=ExportEntity.BILL,
        content_type="text/csv",
    )

    with pytest.raises(HTTPException) as exc_info:
        await request_upload(
            request=request,
            authenticated_client_id=test_client_id,
            cloud_storage=mock_cloud_storage,
        )

    assert exc_info.value.status_code == 400
    assert "Unsupported file extension" in exc_info.value.detail


@pytest.mark.asyncio
async def test_request_upload_requires_cloud_storage(test_client_id):
    """Test that request-upload fails without cloud storage."""
    request = ImportRequestUploadRequest(
        filename="bills.csv",
        entity=ExportEntity.BILL,
        content_type="text/csv",
    )

    with pytest.raises(HTTPException) as exc_info:
        await request_upload(
            request=request,
            authenticated_client_id=test_client_id,
            cloud_storage=None,
        )

    assert exc_info.value.status_code == 500
    assert "Cloud storage is not configured" in exc_info.value.detail


# ============================================================================
# Tests for /imports/confirm-upload
# ============================================================================


@pytest.mark.asyncio
async def test_confirm_upload_validates_tenant_isolation(mock_cloud_storage, test_client_id):
    """Test that confirm-upload rejects file_key with wrong client_id."""
    wrong_client_id = uuid4()
    request = ImportConfirmUploadRequest(
        file_key=f"imports/{wrong_client_id}/temp/bills.csv",
        entity=ExportEntity.BILL,
    )

    with pytest.raises(HTTPException) as exc_info:
        await confirm_upload(
            request=request,
            authenticated_client_id=test_client_id,
            cloud_storage=mock_cloud_storage,
        )

    assert exc_info.value.status_code == 403
    assert "Access denied" in exc_info.value.detail


@pytest.mark.asyncio
async def test_confirm_upload_file_not_found(mock_cloud_storage, test_client_id):
    """Test that confirm-upload returns 404 when file doesn't exist."""
    mock_cloud_storage.file_exists = AsyncMock(return_value=False)

    request = ImportConfirmUploadRequest(
        file_key=f"imports/{test_client_id}/temp/bills.csv",
        entity=ExportEntity.BILL,
    )

    with pytest.raises(HTTPException) as exc_info:
        await confirm_upload(
            request=request,
            authenticated_client_id=test_client_id,
            cloud_storage=mock_cloud_storage,
        )

    assert exc_info.value.status_code == 404
    assert "File not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_confirm_upload_validation_failure(mock_cloud_storage, test_client_id, tmp_path):
    """Test that confirm-upload returns 400 for invalid file content."""
    mock_cloud_storage.file_exists = AsyncMock(return_value=True)
    mock_cloud_storage.download_file = AsyncMock(return_value=str(tmp_path / "bills.csv"))

    file_key = f"imports/{test_client_id}/temp/bills.csv"
    request = ImportConfirmUploadRequest(
        file_key=file_key,
        entity=ExportEntity.BILL,
    )

    with (
        patch("app.api.imports.settings") as mock_settings,
        patch("app.api.imports.ImportValidator") as mock_validator,
        patch("app.api.imports.os.path.exists", return_value=False),
        patch("app.api.imports.os.makedirs"),
        patch("app.api.imports.os.remove"),
    ):
        mock_settings.export_local_path = str(tmp_path)
        mock_validator.validate_file_format.return_value = (
            False,
            "Invalid file format",
        )

        response = await confirm_upload(
            request=request,
            authenticated_client_id=test_client_id,
            cloud_storage=mock_cloud_storage,
        )

    assert response.status_code == 400
    content = json.loads(response.body.decode())
    assert content["status"] == "validation_failed"


@pytest.mark.asyncio
async def test_confirm_upload_success(mock_cloud_storage, test_client_id, tmp_path):
    """Test successful confirm-upload with valid CSV."""
    mock_cloud_storage.file_exists = AsyncMock(return_value=True)
    mock_cloud_storage.download_file = AsyncMock(return_value=str(tmp_path / "bills.csv"))

    file_key = f"imports/{test_client_id}/temp/abc123_bills.csv"
    request = ImportConfirmUploadRequest(
        file_key=file_key,
        entity=ExportEntity.BILL,
    )

    with (
        patch("app.api.imports.settings") as mock_settings,
        patch("app.api.imports.ImportValidator") as mock_validator,
        patch("app.api.imports.os.path.exists", return_value=False),
        patch("app.api.imports.os.makedirs"),
        patch("app.api.imports.os.remove"),
    ):
        mock_settings.export_local_path = str(tmp_path)
        mock_validator.validate_file_format.return_value = (True, None)
        mock_validator.validate_import_file = AsyncMock(return_value=(True, []))
        mock_validator.extract_columns.return_value = (
            ["id", "amount", "date"],
            False,
        )

        response = await confirm_upload(
            request=request,
            authenticated_client_id=test_client_id,
            cloud_storage=mock_cloud_storage,
        )

    assert response.status == "validated"
    assert response.file_path == file_key
    assert response.columns == ["id", "amount", "date"]
    assert response.has_action_column is False
    assert response.entity == "bill"
    assert response.filename == "abc123_bills.csv"
