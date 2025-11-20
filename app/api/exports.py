"""API routes for export operations."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dto import (
    ErrorResponse,
    ExportPreviewRequest,
    ExportPreviewResponse,
    ExportRequest,
)
from app.api.dto import (
    ExportResultResponse as ExportResultResponseDTO,
)
from app.auth.backend import get_current_client_id
from app.core.dependency_injection import get_job_service, get_query_engine
from app.domain.entities import ExportConfig, JobStatus, JobType
from app.infrastructure.query.engine import ExportQueryEngine
from app.infrastructure.storage.factory import get_cloud_storage
from app.services.job_service import JobService

router = APIRouter(prefix="/exports", tags=["exports"])


@router.post(
    "",
    response_model=ExportResultResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create export job",
    description="Create and immediately trigger an export job. Returns the job run ID for tracking.",
    responses={
        201: {
            "description": "Export job created and triggered successfully",
            "content": {
                "application/json": {
                    "example": {
                        "run_id": "550e8400-e29b-41d4-a716-446655440000",
                        "entity": "bill",
                        "status": "pending",
                        "result_metadata": None,
                        "error_message": None,
                    }
                }
            },
        },
        400: {"description": "Invalid export request", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def create_export(
    export_request: ExportRequest,
    authenticated_client_id: UUID = Depends(get_current_client_id),
    job_service: JobService = Depends(get_job_service),
):
    """
    Create and trigger an export job.

    The client_id is extracted from the JWT token, not from the URL path.
    This prevents clients from accessing other clients' data by manipulating URLs.

    **Request Body:**
    - `entity`: Entity type to export (bill, invoice, vendor, project)
    - `fields`: List of fields to include in the export
    - `filters`: Optional filters to apply
    - `sort`: Optional sorting configuration
    - `limit`: Maximum number of records (default: 100)
    - `offset`: Number of records to skip (default: 0)

    **Example Request:**
    ```json
    {
        "entity": "bill",
        "fields": ["id", "amount", "date", "vendor.name"],
        "filters": [
            {
                "field": "amount",
                "operator": "gte",
                "value": 1000
            }
        ],
        "sort": [{"field": "date", "direction": "desc"}],
        "limit": 50
    }
    ```
    """
    try:
        from uuid import uuid4

        from app.domain.entities import JobDefinition

        # Create export config
        export_config = ExportConfig(
            entity=export_request.entity,
            fields=export_request.fields,
            filters=export_request.filters,
            sort=export_request.sort,
            limit=export_request.limit,
            offset=export_request.offset,
        )

        # Create a one-time job for this export
        # Use client_id from JWT token (authenticated_client_id)
        job = JobDefinition(
            id=uuid4(),
            client_id=authenticated_client_id,  # From JWT token - trusted source
            name=f"Export {export_request.entity.value} - {uuid4()}",
            job_type=JobType.EXPORT,
            export_config=export_config,
            enabled=True,
        )

        created_job = await job_service.create_job(job)
        job_run = await job_service.run_job(created_job.id)

        return ExportResultResponseDTO(
            run_id=job_run.id,
            entity=export_request.entity,
            status=job_run.status,
            result_metadata=job_run.result_metadata,
            error_message=job_run.error_message,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.post(
    "/preview",
    response_model=ExportPreviewResponse,
    responses={400: {"model": ErrorResponse}},
)
async def preview_export(
    preview_request: ExportPreviewRequest,
    authenticated_client_id: UUID = Depends(get_current_client_id),
    query_engine: ExportQueryEngine = Depends(get_query_engine),
):
    """
    Preview export results without creating a job.

    The client_id is extracted from the JWT token. This endpoint allows clients
    to preview what data would be exported before creating an actual export job.
    """
    try:
        # Create export config with limited results for preview
        export_config = ExportConfig(
            entity=preview_request.entity,
            fields=preview_request.fields,
            filters=preview_request.filters,
            sort=preview_request.sort,
            limit=preview_request.limit,
            offset=0,
        )

        # Execute query to get preview
        result = await query_engine.execute_export_query(export_config)

        return ExportPreviewResponse(
            entity=preview_request.entity,
            count=result.get("count", 0),
            records=result.get("records", [])[: preview_request.limit],
            limit=preview_request.limit,
            offset=0,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.get(
    "/{run_id}/result",
    response_model=ExportResultResponseDTO,
    responses={404: {"model": ErrorResponse}},
)
async def get_export_result(
    run_id: UUID,
    authenticated_client_id: UUID = Depends(get_current_client_id),
    job_service: JobService = Depends(get_job_service),
):
    """Get export result for a completed job run."""
    try:
        job_run = await job_service.get_job_run(run_id)

        # Verify job belongs to authenticated client
        job = await job_service.get_job(job_run.job_id)
        if job.client_id != authenticated_client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Job does not belong to authenticated client.",
            )

        if not job.export_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job is not an export job",
            )

        # If job is completed and has a remote file, add download URL to metadata
        result_metadata = job_run.result_metadata or {}
        if (
            job_run.status == JobStatus.SUCCEEDED
            and result_metadata.get("remote_file_path")
            and job_run.result_metadata
        ):
            # Download URL will be generated by the download endpoint
            # We don't generate it here to avoid long URLs in the response
            pass

        return ExportResultResponseDTO(
            run_id=job_run.id,
            entity=job.export_config.entity,
            status=job_run.status,
            result_metadata=result_metadata,
            error_message=job_run.error_message,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.get(
    "/{run_id}/download",
    responses={200: {"description": "Pre-signed download URL"}, 404: {"model": ErrorResponse}},
)
async def get_export_download_url(
    run_id: UUID,
    expiration_seconds: int = 3600,
    authenticated_client_id: UUID = Depends(get_current_client_id),
    job_service: JobService = Depends(get_job_service),
):
    """Get a pre-signed URL for downloading the export file."""
    try:
        job_run = await job_service.get_job_run(run_id)

        # Verify job belongs to authenticated client
        job = await job_service.get_job(job_run.job_id)
        if job.client_id != authenticated_client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Job does not belong to authenticated client.",
            )

        if not job.export_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job is not an export job",
            )

        if job_run.status != JobStatus.SUCCEEDED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job run is not completed. Current status: {job_run.status.value}",
            )

        result_metadata = job_run.result_metadata or {}
        remote_file_path = result_metadata.get("remote_file_path")

        if not remote_file_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export file not found. File may not have been uploaded to cloud storage.",
            )

        cloud_storage = get_cloud_storage()
        if not cloud_storage:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cloud storage not configured",
            )

        # Validate expiration_seconds (max 7 days for security)
        max_expiration = 7 * 24 * 60 * 60  # 7 days
        expiration_seconds = min(expiration_seconds, max_expiration)
        expiration_seconds = max(expiration_seconds, 60)  # Minimum 1 minute

        # Generate pre-signed URL
        download_url = await cloud_storage.generate_presigned_url(
            remote_file_path, expiration_seconds=expiration_seconds
        )

        return {
            "run_id": str(run_id),
            "download_url": download_url,
            "expires_in_seconds": expiration_seconds,
            "file_path": remote_file_path,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
