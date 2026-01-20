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
from app.core.logging import get_logger
from app.domain.entities import ExportConfig, JobStatus, JobType
from app.infrastructure.query.engine import ExportQueryEngine
from app.infrastructure.storage.factory import get_cloud_storage
from app.services.job_service import JobService

logger = get_logger(__name__)

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

        # Log request input (excluding PII)
        aliased_count = sum(1 for f in export_request.fields if f.as_ is not None)
        logger.info(
            f"Export request received: client_id={authenticated_client_id}, "
            f"entity={export_request.entity.value}, fields={len(export_request.fields)}, "
            f"aliased_fields={aliased_count}, "
            f"filters={'present' if export_request.filters else 'none'}, "
            f"sort={'present' if export_request.sort else 'none'}, "
            f"limit={export_request.limit}, offset={export_request.offset}"
        )
        if aliased_count > 0:
            aliases = {f.field: f.as_ for f in export_request.fields if f.as_ is not None}
            logger.debug(f"Export field aliases: {aliases}")

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
        # Pass client_id for authorization check
        job_run = await job_service.run_job(created_job.id, client_id=authenticated_client_id)

        # Log response output
        logger.info(
            f"Export job created: job_id={created_job.id}, run_id={job_run.id}, "
            f"status={job_run.status.value}, client_id={authenticated_client_id}"
        )

        return ExportResultResponseDTO(
            run_id=job_run.id,
            entity=export_request.entity,
            status=job_run.status,
            result_metadata=job_run.result_metadata,
            error_message=job_run.error_message,
        )
    except HTTPException:
        # Re-raise HTTP exceptions (e.g., from validation)
        raise
    except ValueError as e:
        # Convert ValueError to HTTPException for validation errors
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    # ApplicationError will be handled by global exception handler


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
        # Log request input
        aliased_count = sum(1 for f in preview_request.fields if f.as_ is not None)
        logger.info(
            f"Export preview request: client_id={authenticated_client_id}, "
            f"entity={preview_request.entity.value}, fields={len(preview_request.fields)}, "
            f"aliased_fields={aliased_count}, "
            f"filters={'present' if preview_request.filters else 'none'}, limit={preview_request.limit}"
        )
        if aliased_count > 0:
            aliases = {f.field: f.as_ for f in preview_request.fields if f.as_ is not None}
            logger.debug(f"Preview field aliases: {aliases}")

        # Create export config with limited results for preview
        export_config = ExportConfig(
            entity=preview_request.entity,
            fields=preview_request.fields,
            filters=preview_request.filters,
            sort=preview_request.sort,
            limit=preview_request.limit,
            offset=0,
        )

        # Execute query to get preview (pass client_id for security)
        result = await query_engine.execute_export_query(
            export_config, client_id=authenticated_client_id
        )

        record_count = len(result.get("records", []))
        # Log response output
        logger.info(
            f"Export preview completed: client_id={authenticated_client_id}, "
            f"entity={preview_request.entity.value}, total_count={result.get('count', 0)}, "
            f"records_returned={record_count}"
        )

        return ExportPreviewResponse(
            entity=preview_request.entity,
            count=result.get("count", 0),
            records=result.get("records", [])[: preview_request.limit],
            limit=preview_request.limit,
            offset=0,
        )
    except HTTPException:
        # Re-raise HTTP exceptions (e.g., from validation)
        raise
    except ValueError as e:
        # Convert ValueError to HTTPException for validation errors
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    # ApplicationError will be handled by global exception handler


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
        # Log request input
        logger.info(
            f"Get export result request: run_id={run_id}, client_id={authenticated_client_id}"
        )

        job_run = await job_service.get_job_run(run_id)

        # Verify job belongs to authenticated client
        job = await job_service.get_job(job_run.job_id)
        if job.client_id != authenticated_client_id:
            logger.warning(
                f"Access denied: run_id={run_id}, requested_client_id={authenticated_client_id}, "
                f"job_client_id={job.client_id}"
            )
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

        # Log response output
        logger.info(
            f"Export result retrieved: run_id={run_id}, job_id={job.id}, "
            f"status={job_run.status.value}, entity={job.export_config.entity.value}, "
            f"has_file={'yes' if result_metadata.get('remote_file_path') else 'no'}"
        )

        return ExportResultResponseDTO(
            run_id=job_run.id,
            entity=job.export_config.entity,
            status=job_run.status,
            result_metadata=result_metadata,
            error_message=job_run.error_message,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    # Generic exceptions are handled by global exception handler for secure error messages


@router.get(
    "/{run_id}/download",
    responses={
        200: {"description": "Pre-signed download URL or redirect to file"},
        404: {"model": ErrorResponse},
    },
)
async def get_export_download_url(
    run_id: UUID,
    expiration_seconds: int = 3600,
    authenticated_client_id: UUID = Depends(get_current_client_id),
    job_service: JobService = Depends(get_job_service),
):
    """Get a pre-signed URL for downloading the export file."""
    try:
        # Log request input
        logger.info(
            f"Get export download URL request: run_id={run_id}, "
            f"client_id={authenticated_client_id}, expiration_seconds={expiration_seconds}"
        )

        job_run = await job_service.get_job_run(run_id)

        # Verify job belongs to authenticated client
        job = await job_service.get_job(job_run.job_id)
        if job.client_id != authenticated_client_id:
            logger.warning(
                f"Access denied for download URL: run_id={run_id}, "
                f"requested_client_id={authenticated_client_id}, job_client_id={job.client_id}"
            )
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
        local_file_path = result_metadata.get("local_file_path")

        cloud_storage = get_cloud_storage()

        # If we have a remote file and cloud storage is configured, return presigned URL
        if remote_file_path and cloud_storage:
            # Validate expiration_seconds (max 7 days for security)
            max_expiration = 7 * 24 * 60 * 60  # 7 days
            expiration_seconds = min(expiration_seconds, max_expiration)
            expiration_seconds = max(expiration_seconds, 60)  # Minimum 1 minute

            # Generate pre-signed URL
            download_url = await cloud_storage.generate_presigned_url(
                remote_file_path, expiration_seconds=expiration_seconds
            )

            logger.info(
                f"Export download URL generated: run_id={run_id}, file_path={remote_file_path}, "
                f"expires_in_seconds={expiration_seconds}, url_length={len(download_url)}"
            )

            return {
                "run_id": str(run_id),
                "download_url": download_url,
                "expires_in_seconds": expiration_seconds,
                "file_path": remote_file_path,
            }

        # If we have a local file (development mode), return URL to file endpoint
        if local_file_path:
            import os

            if not os.path.exists(local_file_path):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Local export file not found: {local_file_path}",
                )

            # Return URL to file download endpoint
            download_url = f"/exports/{run_id}/file"
            logger.info(
                f"Export local file URL generated: run_id={run_id}, local_path={local_file_path}"
            )

            return {
                "run_id": str(run_id),
                "download_url": download_url,
                "expires_in_seconds": None,
                "file_path": local_file_path,
            }

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export file not found. File may not have been generated or uploaded.",
        )
    except HTTPException:
        # Re-raise HTTP exceptions (e.g., from access denied checks)
        raise
    # ApplicationError (e.g., NotFoundError) will be handled by global exception handler


@router.get(
    "/{run_id}/file",
    responses={200: {"description": "Export file download"}, 404: {"model": ErrorResponse}},
)
async def download_export_file(
    run_id: UUID,
    authenticated_client_id: UUID = Depends(get_current_client_id),
    job_service: JobService = Depends(get_job_service),
):
    """Download the export file directly (for local development without cloud storage)."""
    from pathlib import Path

    from fastapi.responses import FileResponse

    from app.core.config import get_settings

    try:
        logger.info(
            f"Download export file request: run_id={run_id}, client_id={authenticated_client_id}"
        )

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
        local_file_path = result_metadata.get("local_file_path")

        if not local_file_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export file not found.",
            )

        # Path traversal protection: ensure file is within allowed exports directory
        settings = get_settings()
        allowed_dir = Path(settings.export_local_path).resolve()
        requested_path = Path(local_file_path).resolve()

        # Verify the resolved path is within the allowed directory
        try:
            requested_path.relative_to(allowed_dir)
        except ValueError:
            logger.warning(
                f"Path traversal attempt blocked: run_id={run_id}, "
                f"requested_path={local_file_path}, allowed_dir={allowed_dir}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Invalid file path.",
            ) from None

        if not requested_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export file not found.",
            )

        # Determine content type based on file extension
        filename = requested_path.name
        if requested_path.suffix == ".csv":
            media_type = "text/csv"
        elif requested_path.suffix == ".json":
            media_type = "application/json"
        else:
            media_type = "application/octet-stream"

        logger.info(f"Serving export file: run_id={run_id}, file={filename}")

        return FileResponse(
            path=str(requested_path),
            filename=filename,
            media_type=media_type,
        )
    except HTTPException:
        raise
