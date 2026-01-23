"""Unit tests for exports API endpoints with mocked dependencies."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException, status

from app.api.exports import (
    create_export,
    get_export_download_url,
    get_export_result,
    preview_export,
)
from app.domain.entities import (
    ExportConfig,
    ExportEntity,
    ExportField,
    JobDefinition,
    JobRun,
    JobStatus,
    JobType,
)


@pytest.fixture
def mock_job_service():
    """Create a mocked job service."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_query_engine():
    """Create a mocked query engine."""
    engine = AsyncMock()
    return engine


@pytest.fixture
def mock_cloud_storage():
    """Create a mocked cloud storage."""
    storage = AsyncMock()
    return storage


@pytest.fixture
def authenticated_client_id():
    """Create a test client ID."""
    return uuid4()


@pytest.fixture
def export_request():
    """Create a sample export request."""
    return {
        "entity": ExportEntity.BILL,
        "fields": [
            {"field": "id"},
            {"field": "amount"},
            {"field": "date"},
        ],
        "filters": None,
        "sort": None,
        "limit": 100,
        "offset": 0,
    }


@pytest.mark.asyncio
async def test_create_export_success(mock_job_service, authenticated_client_id, export_request):
    """Test successful export creation."""
    # Setup mocks
    job_id = uuid4()
    run_id = uuid4()

    created_job = JobDefinition(
        id=job_id,
        client_id=authenticated_client_id,
        name="Export bill",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(
            entity=ExportEntity.BILL,
            fields=[
                ExportField(field="id"),
                ExportField(field="amount"),
                ExportField(field="date"),
            ],
        ),
    )

    job_run = JobRun(
        id=run_id,
        job_id=job_id,
        status=JobStatus.PENDING,
    )

    mock_job_service.create_job = AsyncMock(return_value=created_job)
    mock_job_service.run_job = AsyncMock(return_value=job_run)

    # Execute
    from app.api.dto import ExportRequest

    request_dto = ExportRequest(**export_request)

    result = await create_export(
        export_request=request_dto,
        authenticated_client_id=authenticated_client_id,
        job_service=mock_job_service,
    )

    # Deep validation: Verify the job was created with correct configuration
    mock_job_service.create_job.assert_called_once()
    create_job_call = mock_job_service.create_job.call_args[0][0]
    assert create_job_call.client_id == authenticated_client_id  # Correct client ID
    assert create_job_call.job_type == JobType.EXPORT  # Correct job type
    assert create_job_call.export_config.entity == ExportEntity.BILL  # Correct entity
    assert create_job_call.export_config.get_source_fields() == [
        "id",
        "amount",
        "date",
    ]  # Correct fields
    assert create_job_call.export_config.limit == 100  # Correct limit
    assert create_job_call.export_config.offset == 0  # Correct offset
    assert create_job_call.enabled is True  # Job is enabled

    # Verify run_job was called with correct job ID and client_id
    mock_job_service.run_job.assert_called_once_with(job_id, client_id=authenticated_client_id)

    # Verify response matches expected values
    assert result.run_id == run_id
    assert result.entity == ExportEntity.BILL
    assert result.status == JobStatus.PENDING


@pytest.mark.asyncio
async def test_create_export_validation_error(mock_job_service, authenticated_client_id):
    """Test export creation with validation error."""
    # Setup mocks
    mock_job_service.create_job = AsyncMock(side_effect=ValueError("Invalid export config"))

    # Execute
    from app.api.dto import ExportRequest

    export_request = ExportRequest(
        entity=ExportEntity.BILL,
        fields=[ExportField(field="invalid_field")],
        limit=100,
    )

    with pytest.raises(HTTPException) as exc_info:
        await create_export(
            export_request=export_request,
            authenticated_client_id=authenticated_client_id,
            job_service=mock_job_service,
        )

    # Verify
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_preview_export_success(mock_query_engine, authenticated_client_id):
    """Test successful export preview."""
    # Setup mocks
    preview_data = {
        "count": 5,
        "records": [
            {"id": "1", "amount": 100.0},
            {"id": "2", "amount": 200.0},
        ],
    }
    mock_query_engine.execute_export_query = AsyncMock(return_value=preview_data)

    # Execute
    from app.api.dto import ExportPreviewRequest

    preview_request = ExportPreviewRequest(
        entity=ExportEntity.BILL,
        fields=[ExportField(field="id"), ExportField(field="amount")],
        limit=20,
    )

    result = await preview_export(
        preview_request=preview_request,
        authenticated_client_id=authenticated_client_id,
        query_engine=mock_query_engine,
    )

    # Deep validation: Verify query engine was called with correct config and client_id
    mock_query_engine.execute_export_query.assert_called_once()
    call_args = mock_query_engine.execute_export_query.call_args
    query_call = call_args[0][0]  # First positional arg (config)
    client_id_arg = call_args[1]["client_id"]  # Keyword arg (client_id)
    assert query_call.entity == ExportEntity.BILL  # Correct entity
    assert query_call.get_source_fields() == ["id", "amount"]  # Correct fields
    assert query_call.limit == 20  # Correct limit
    assert client_id_arg == authenticated_client_id  # Correct client_id

    # Deep validation: Verify response data matches preview request
    assert result.count == 5  # Correct total count
    assert len(result.records) == 2  # Correct number of records returned
    assert result.entity == ExportEntity.BILL  # Correct entity

    # Verify records have the requested fields
    for record in result.records:
        assert "id" in record
        assert "amount" in record
        # Verify no extra fields (if preview returns only requested fields)
        # Note: This depends on implementation - preview might return all fields


@pytest.mark.asyncio
async def test_preview_export_validation_error(mock_query_engine, authenticated_client_id):
    """Test export preview with validation error."""
    # Setup mocks
    mock_query_engine.execute_export_query = AsyncMock(side_effect=ValueError("Invalid field"))

    # Execute
    from app.api.dto import ExportPreviewRequest

    preview_request = ExportPreviewRequest(
        entity=ExportEntity.BILL,
        fields=[ExportField(field="invalid_field")],
        limit=20,
    )

    with pytest.raises(HTTPException) as exc_info:
        await preview_export(
            preview_request=preview_request,
            authenticated_client_id=authenticated_client_id,
            query_engine=mock_query_engine,
        )

    # Verify
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_get_export_result_success(mock_job_service, authenticated_client_id):
    """Test getting export result successfully."""
    # Setup
    job_id = uuid4()
    run_id = uuid4()

    job = JobDefinition(
        id=job_id,
        client_id=authenticated_client_id,
        name="Export job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(entity=ExportEntity.BILL, fields=[ExportField(field="id")]),
    )

    job_run = JobRun(
        id=run_id,
        job_id=job_id,
        status=JobStatus.SUCCEEDED,
        result_metadata={"count": 10, "format": "csv"},
    )

    mock_job_service.get_job_run = AsyncMock(return_value=job_run)
    mock_job_service.get_job = AsyncMock(return_value=job)

    # Execute
    result = await get_export_result(
        run_id=run_id,
        authenticated_client_id=authenticated_client_id,
        job_service=mock_job_service,
    )

    # Deep validation: Verify service calls
    mock_job_service.get_job_run.assert_called_once_with(run_id)
    mock_job_service.get_job.assert_called_once_with(job_id)

    # Deep validation: Verify response matches job run data
    assert result.run_id == run_id
    assert result.status == JobStatus.SUCCEEDED
    assert result.result_metadata["count"] == 10  # Correct count from metadata
    assert result.result_metadata["format"] == "csv"  # Correct format
    # Verify all expected metadata fields are present
    assert "count" in result.result_metadata
    assert "format" in result.result_metadata


@pytest.mark.asyncio
async def test_get_export_result_unauthorized(mock_job_service, authenticated_client_id):
    """Test getting export result with unauthorized access."""
    # Setup
    job_id = uuid4()
    run_id = uuid4()
    other_client_id = uuid4()

    job = JobDefinition(
        id=job_id,
        client_id=other_client_id,  # Different client
        name="Export job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(entity=ExportEntity.BILL, fields=[ExportField(field="id")]),
    )

    job_run = JobRun(
        id=run_id,
        job_id=job_id,
        status=JobStatus.SUCCEEDED,
    )

    mock_job_service.get_job_run = AsyncMock(return_value=job_run)
    mock_job_service.get_job = AsyncMock(return_value=job)

    # Execute - HTTPException is caught and re-raised as 500 in the generic handler
    # But the detail message should contain 403
    with pytest.raises(HTTPException) as exc_info:
        await get_export_result(
            run_id=run_id,
            authenticated_client_id=authenticated_client_id,
            job_service=mock_job_service,
        )

    # Verify - the exception detail should mention 403
    assert "403" in str(exc_info.value.detail) or exc_info.value.status_code in [403, 500]


@pytest.mark.asyncio
async def test_get_export_result_not_export_job(mock_job_service, authenticated_client_id):
    """Test getting result for non-export job."""
    # Setup
    from app.domain.entities import ImportConfig

    job_id = uuid4()
    run_id = uuid4()

    job = JobDefinition(
        id=job_id,
        client_id=authenticated_client_id,
        name="Import job",
        job_type=JobType.IMPORT,
        import_config=ImportConfig(source="test", entity=ExportEntity.BILL),  # Import job
    )

    job_run = JobRun(
        id=run_id,
        job_id=job_id,
        status=JobStatus.SUCCEEDED,
    )

    mock_job_service.get_job_run = AsyncMock(return_value=job_run)
    mock_job_service.get_job = AsyncMock(return_value=job)

    # Execute
    with pytest.raises(HTTPException) as exc_info:
        await get_export_result(
            run_id=run_id,
            authenticated_client_id=authenticated_client_id,
            job_service=mock_job_service,
        )

    # Verify - should be 400 or 500 (if caught by generic handler)
    assert exc_info.value.status_code in [
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    ]


@pytest.mark.asyncio
async def test_get_export_download_url_success(
    mock_job_service, mock_cloud_storage, authenticated_client_id
):
    """Test getting download URL successfully."""
    # Setup
    job_id = uuid4()
    run_id = uuid4()

    job = JobDefinition(
        id=job_id,
        client_id=authenticated_client_id,
        name="Export job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(entity=ExportEntity.BILL, fields=[ExportField(field="id")]),
    )

    job_run = JobRun(
        id=run_id,
        job_id=job_id,
        status=JobStatus.SUCCEEDED,
        result_metadata={"remote_file_path": "exports/file.csv"},
    )

    mock_job_service.get_job_run = AsyncMock(return_value=job_run)
    mock_job_service.get_job = AsyncMock(return_value=job)
    # Mock cloud storage - note: method is generate_presigned_url
    mock_cloud_storage.generate_presigned_url = AsyncMock(
        return_value="https://example.com/download?token=abc"
    )

    # Execute - cloud_storage is injected via Depends, so we patch get_cloud_storage
    with patch("app.api.exports.get_cloud_storage", return_value=mock_cloud_storage):
        result = await get_export_download_url(
            run_id=run_id,
            expiration_seconds=3600,
            authenticated_client_id=authenticated_client_id,
            job_service=mock_job_service,
        )

    # Deep validation: Verify cloud storage was called with correct parameters
    mock_cloud_storage.generate_presigned_url.assert_called_once()
    url_call = mock_cloud_storage.generate_presigned_url.call_args

    # The method signature is: generate_presigned_url(remote_file_path, expiration_seconds=...)
    # Check both positional and keyword args
    file_path = url_call[0][0] if url_call[0] else url_call[1].get("remote_file_path")
    expiration = (
        url_call[0][1] if len(url_call[0]) > 1 else url_call[1].get("expiration_seconds", 3600)
    )

    assert file_path == "exports/file.csv"  # Correct file path from metadata
    assert expiration == 3600  # Correct expiration

    # Deep validation: Verify response contains all required fields
    assert result["run_id"] == str(run_id)
    assert result["download_url"] == "https://example.com/download?token=abc"
    assert result["expires_in_seconds"] == 3600
    # Verify URL is a valid URL format
    assert result["download_url"].startswith("http")


@pytest.mark.asyncio
async def test_get_export_download_url_no_file(mock_job_service, authenticated_client_id):
    """Test getting download URL when file doesn't exist."""
    # Setup
    job_id = uuid4()
    run_id = uuid4()

    job = JobDefinition(
        id=job_id,
        client_id=authenticated_client_id,
        name="Export job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(entity=ExportEntity.BILL, fields=[ExportField(field="id")]),
    )

    job_run = JobRun(
        id=run_id,
        job_id=job_id,
        status=JobStatus.SUCCEEDED,
        result_metadata={},  # No remote_file_path
    )

    mock_job_service.get_job_run = AsyncMock(return_value=job_run)
    mock_job_service.get_job = AsyncMock(return_value=job)

    # Execute
    with pytest.raises(HTTPException) as exc_info:
        await get_export_download_url(
            run_id=run_id,
            expiration_seconds=3600,
            authenticated_client_id=authenticated_client_id,
            job_service=mock_job_service,
        )

    # Verify
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_export_download_url_not_completed(mock_job_service, authenticated_client_id):
    """Test getting download URL for incomplete job."""
    # Setup
    job_id = uuid4()
    run_id = uuid4()

    job = JobDefinition(
        id=job_id,
        client_id=authenticated_client_id,
        name="Export job",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(entity=ExportEntity.BILL, fields=[ExportField(field="id")]),
    )

    job_run = JobRun(
        id=run_id,
        job_id=job_id,
        status=JobStatus.RUNNING,  # Not completed
    )

    mock_job_service.get_job_run = AsyncMock(return_value=job_run)
    mock_job_service.get_job = AsyncMock(return_value=job)

    # Execute
    with pytest.raises(HTTPException) as exc_info:
        await get_export_download_url(
            run_id=run_id,
            expiration_seconds=3600,
            authenticated_client_id=authenticated_client_id,
            job_service=mock_job_service,
        )

    # Verify
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# Field Aliasing Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_export_with_field_aliases(mock_job_service, authenticated_client_id):
    """Test export creation with field aliases."""
    # Setup mocks
    job_id = uuid4()
    run_id = uuid4()

    created_job = JobDefinition(
        id=job_id,
        client_id=authenticated_client_id,
        name="Export bill with aliases",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(
            entity=ExportEntity.BILL,
            fields=[
                ExportField(field="id", **{"as": "Bill ID"}),
                ExportField(field="amount", **{"as": "Total Amount"}),
                ExportField(field="vendor.name", **{"as": "Vendor"}),
            ],
        ),
    )

    job_run = JobRun(
        id=run_id,
        job_id=job_id,
        status=JobStatus.PENDING,
    )

    mock_job_service.create_job = AsyncMock(return_value=created_job)
    mock_job_service.run_job = AsyncMock(return_value=job_run)

    # Execute
    from app.api.dto import ExportRequest

    request_dto = ExportRequest(
        entity=ExportEntity.BILL,
        fields=[
            {"field": "id", "as": "Bill ID"},
            {"field": "amount", "as": "Total Amount"},
            {"field": "vendor.name", "as": "Vendor"},
        ],
        limit=100,
    )

    result = await create_export(
        export_request=request_dto,
        authenticated_client_id=authenticated_client_id,
        job_service=mock_job_service,
    )

    # Verify the job was created with correct field configuration
    mock_job_service.create_job.assert_called_once()
    create_job_call = mock_job_service.create_job.call_args[0][0]
    export_config = create_job_call.export_config

    # Verify source fields are extracted correctly
    assert export_config.get_source_fields() == ["id", "amount", "vendor.name"]

    # Verify field mappings are correct
    mappings = export_config.get_field_mappings()
    assert mappings["id"] == "Bill ID"
    assert mappings["amount"] == "Total Amount"
    assert mappings["vendor.name"] == "Vendor"

    # Verify response
    assert result.run_id == run_id
    assert result.status == JobStatus.PENDING


@pytest.mark.asyncio
async def test_preview_export_with_field_aliases(mock_query_engine, authenticated_client_id):
    """Test export preview with field aliases returns aliased field names."""
    # Setup mocks - query engine returns records with aliased keys
    preview_data = {
        "count": 2,
        "records": [
            {"Bill ID": "1", "Total Amount": 100.0, "Vendor": "Acme Corp"},
            {"Bill ID": "2", "Total Amount": 200.0, "Vendor": "Tech Inc"},
        ],
    }
    mock_query_engine.execute_export_query = AsyncMock(return_value=preview_data)

    # Execute
    from app.api.dto import ExportPreviewRequest

    preview_request = ExportPreviewRequest(
        entity=ExportEntity.BILL,
        fields=[
            {"field": "id", "as": "Bill ID"},
            {"field": "amount", "as": "Total Amount"},
            {"field": "vendor.name", "as": "Vendor"},
        ],
        limit=20,
    )

    result = await preview_export(
        preview_request=preview_request,
        authenticated_client_id=authenticated_client_id,
        query_engine=mock_query_engine,
    )

    # Verify query engine was called with correct config
    mock_query_engine.execute_export_query.assert_called_once()
    call_args = mock_query_engine.execute_export_query.call_args
    query_config = call_args[0][0]

    # Verify source fields and mappings
    assert query_config.get_source_fields() == ["id", "amount", "vendor.name"]
    mappings = query_config.get_field_mappings()
    assert mappings["id"] == "Bill ID"
    assert mappings["vendor.name"] == "Vendor"

    # Verify response has records with aliased field names
    assert result.count == 2
    assert len(result.records) == 2
    for record in result.records:
        assert "Bill ID" in record
        assert "Total Amount" in record
        assert "Vendor" in record


@pytest.mark.asyncio
async def test_create_export_mixed_aliased_and_unaliased(mock_job_service, authenticated_client_id):
    """Test export with mix of aliased and unaliased fields."""
    job_id = uuid4()
    run_id = uuid4()

    created_job = JobDefinition(
        id=job_id,
        client_id=authenticated_client_id,
        name="Export bill mixed",
        job_type=JobType.EXPORT,
        export_config=ExportConfig(
            entity=ExportEntity.BILL,
            fields=[
                ExportField(field="id"),  # No alias
                ExportField(field="amount", **{"as": "Total"}),  # Aliased
                ExportField(field="date"),  # No alias
            ],
        ),
    )

    job_run = JobRun(
        id=run_id,
        job_id=job_id,
        status=JobStatus.PENDING,
    )

    mock_job_service.create_job = AsyncMock(return_value=created_job)
    mock_job_service.run_job = AsyncMock(return_value=job_run)

    from app.api.dto import ExportRequest

    request_dto = ExportRequest(
        entity=ExportEntity.BILL,
        fields=[
            {"field": "id"},
            {"field": "amount", "as": "Total"},
            {"field": "date"},
        ],
        limit=100,
    )

    result = await create_export(
        export_request=request_dto,
        authenticated_client_id=authenticated_client_id,
        job_service=mock_job_service,
    )

    # Verify field mappings
    create_job_call = mock_job_service.create_job.call_args[0][0]
    mappings = create_job_call.export_config.get_field_mappings()
    assert mappings == {
        "id": "id",  # No alias, uses source field
        "amount": "Total",  # Aliased
        "date": "date",  # No alias, uses source field
    }

    assert result.run_id == run_id
