"""API routes for import operations."""

import os
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.api.dto import (
    ErrorResponse,
    ImportConfirmUploadRequest,
    ImportConfirmUploadResponse,
    ImportExecuteRequest,
    ImportPreviewRequest,
    ImportPreviewResponse,
    ImportRequestUploadRequest,
    ImportRequestUploadResponse,
)
from app.auth.backend import get_current_client_id
from app.core.config import get_settings
from app.core.dependency_injection import get_cloud_storage, get_job_service
from app.core.logging import get_logger
from app.infrastructure.storage.interface import CloudStorageInterface
from app.services.import_validator import ImportValidator
from app.services.job_service import JobService

logger = get_logger(__name__)
router = APIRouter(prefix="/imports", tags=["imports"])
settings = get_settings()


@router.post(
    "/request-upload",
    response_model=ImportRequestUploadResponse,
    summary="Request a presigned URL for direct file upload",
    description="""
    Step 1 of the presigned upload flow: get a presigned URL for uploading a file
    directly to cloud storage, bypassing API Gateway size limits.

    After receiving the URL, upload the file directly using an HTTP PUT request,
    then call `/imports/confirm-upload` to validate the file.
    """,
    responses={
        200: {"description": "Presigned upload URL generated"},
        400: {"description": "Invalid content type or filename", "model": ErrorResponse},
        500: {"description": "Cloud storage not configured", "model": ErrorResponse},
    },
)
async def request_upload(
    request: ImportRequestUploadRequest,
    authenticated_client_id: UUID = Depends(get_current_client_id),
    cloud_storage: CloudStorageInterface = Depends(get_cloud_storage),
) -> ImportRequestUploadResponse:
    """Request a presigned URL for uploading an import file directly to cloud storage."""
    from app.core.constants import ALLOWED_FILE_EXTENSIONS, ALLOWED_UPLOAD_CONTENT_TYPES

    logger.info(
        f"Presigned upload URL request: client_id={authenticated_client_id}, "
        f"filename={request.filename}, entity={request.entity.value}, "
        f"content_type={request.content_type}"
    )

    # Validate content type
    if request.content_type not in ALLOWED_UPLOAD_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported content type: {request.content_type}. "
            f"Allowed types: {', '.join(sorted(ALLOWED_UPLOAD_CONTENT_TYPES))}",
        )

    # Validate filename extension
    _, ext = os.path.splitext(request.filename)
    if ext.lower() not in ALLOWED_FILE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension: {ext}. "
            f"Allowed extensions: {', '.join(sorted(ALLOWED_FILE_EXTENSIONS))}",
        )

    if not cloud_storage:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloud storage is not configured. Presigned uploads require cloud storage.",
        )

    # Generate S3 key with UUID to avoid collisions
    file_key = f"imports/{authenticated_client_id}/temp/{uuid4()}_{request.filename}"
    expiration = settings.presigned_url_expiration or 3600

    try:
        upload_url = await cloud_storage.generate_presigned_upload_url(
            file_key, request.content_type, expiration_seconds=expiration
        )
    except Exception as e:
        logger.error(f"Failed to generate presigned upload URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate upload URL",
        ) from e

    logger.info(
        f"Presigned upload URL generated: client_id={authenticated_client_id}, "
        f"file_key={file_key}, expires_in={expiration}"
    )

    return ImportRequestUploadResponse(
        upload_url=upload_url,
        file_key=file_key,
        expires_in=expiration,
    )


@router.post(
    "/confirm-upload",
    response_model=ImportConfirmUploadResponse,
    summary="Confirm and validate a file uploaded via presigned URL",
    description="""
    Step 2 of the presigned upload flow: after uploading a file directly to cloud storage
    using the presigned URL from `/request-upload`, call this endpoint to validate
    the file and get column information for the mapping UI.

    The `file_key` from the `/request-upload` response must be provided.
    The validated `file_path` can then be passed to `/preview` or `/execute`.
    """,
    responses={
        200: {"description": "File validated successfully"},
        400: {"description": "Validation failed", "model": ErrorResponse},
        403: {"description": "Tenant isolation violation", "model": ErrorResponse},
        404: {"description": "File not found in cloud storage", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def confirm_upload(
    request: ImportConfirmUploadRequest,
    authenticated_client_id: UUID = Depends(get_current_client_id),
    cloud_storage: CloudStorageInterface = Depends(get_cloud_storage),
) -> ImportConfirmUploadResponse | JSONResponse:
    """Confirm and validate a file that was uploaded via presigned URL."""
    logger.info(
        f"Confirm upload request: client_id={authenticated_client_id}, "
        f"file_key={request.file_key}, entity={request.entity.value}"
    )

    # Verify tenant isolation — file_key must start with this client's prefix
    expected_prefix = f"imports/{authenticated_client_id}/"
    if not request.file_key.startswith(expected_prefix):
        logger.warning(
            f"Tenant isolation violation: client_id={authenticated_client_id}, "
            f"file_key={request.file_key}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: file does not belong to this client",
        )

    if not cloud_storage:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloud storage is not configured",
        )

    # Verify the file exists in cloud storage
    try:
        exists = await cloud_storage.file_exists(request.file_key)
    except Exception as e:
        logger.error(f"Failed to check file existence: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify file in cloud storage",
        ) from e

    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found in cloud storage. Ensure the file was uploaded successfully.",
        )

    # Download file to local temp path for validation
    temp_dir = settings.export_local_path or "/tmp"
    os.makedirs(temp_dir, exist_ok=True)
    filename = os.path.basename(request.file_key)
    temp_file_path = os.path.join(temp_dir, f"confirm_{authenticated_client_id}_{filename}")

    try:
        await cloud_storage.download_file(request.file_key, temp_file_path)

        # Validate file format
        is_valid, format_error = ImportValidator.validate_file_format(temp_file_path)
        if not is_valid:
            logger.warning(
                f"File format validation failed: file_key={request.file_key}, error={format_error}"
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "validation_failed",
                    "message": "File format validation failed",
                    "validation_errors": [{"row": 0, "message": format_error}],
                    "error_count": 1,
                },
            )

        # Validate file content
        is_valid, validation_errors = await ImportValidator.validate_import_file(
            temp_file_path, request.entity
        )
        if not is_valid:
            error_count = len(validation_errors)
            logger.warning(
                f"File content validation failed: file_key={request.file_key}, "
                f"entity={request.entity.value}, error_count={error_count}"
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "validation_failed",
                    "message": "File validation failed",
                    "validation_errors": validation_errors,
                    "error_count": error_count,
                },
            )

        # Extract columns
        columns, has_action_column = ImportValidator.extract_columns(temp_file_path)

        logger.info(
            f"Confirm upload validated: client_id={authenticated_client_id}, "
            f"file_key={request.file_key}, entity={request.entity.value}, "
            f"columns={len(columns)}, has_action_column={has_action_column}"
        )

        return ImportConfirmUploadResponse(
            status="validated",
            message="File uploaded and validated successfully",
            file_path=request.file_key,
            entity=request.entity.value,
            filename=filename,
            columns=columns,
            has_action_column=has_action_column,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during confirm-upload: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate uploaded file",
        ) from e
    finally:
        # Clean up local temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@router.post(
    "/preview",
    response_model=ImportPreviewResponse,
    summary="Preview import with validation",
    description="""
    Preview all records from an uploaded file with validation status for each row.

    This endpoint:
    1. Reads the uploaded file
    2. Applies field mappings (if provided)
    3. Validates each record against the entity schema
    4. Returns all records with their validation status (valid/invalid)

    Use this to review data before executing the import. The response shows:
    - Total record count
    - Valid and invalid counts
    - Each record with its data, validation status, and any errors

    The `file_path` should be obtained from the `/confirm-upload` endpoint.
    """,
    responses={
        200: {
            "description": "Preview generated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "file_path": "imports/client-123/temp/bills.csv",
                        "entity": "bill",
                        "total_records": 100,
                        "valid_count": 95,
                        "invalid_count": 5,
                        "records": [
                            {
                                "row": 1,
                                "data": {"amount": 1000, "date": "2024-01-15"},
                                "is_valid": True,
                                "errors": [],
                            }
                        ],
                    }
                }
            },
        },
        400: {"description": "Invalid request or file not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def preview_import(
    request: ImportPreviewRequest,
    authenticated_client_id: UUID = Depends(get_current_client_id),
    cloud_storage: CloudStorageInterface = Depends(get_cloud_storage),
) -> ImportPreviewResponse:
    """
    Preview import file with validation results.

    Returns all records from the file with validation status for each row.
    This allows users to review which records will succeed and which will fail
    before executing the import.
    """
    try:
        # Log request input
        field_mapping_count = len(request.field_mappings) if request.field_mappings else 0
        logger.info(
            f"Import preview request: client_id={authenticated_client_id}, "
            f"file_path={request.file_path}, entity={request.entity.value}, "
            f"field_mappings_count={field_mapping_count}"
        )
        if request.field_mappings:
            mappings = {fm.source: fm.target for fm in request.field_mappings}
            logger.debug(f"Import field mappings: {mappings}")

        # Determine local file path
        local_file_path = request.file_path

        # If file is in cloud storage, download it first
        if cloud_storage and not os.path.exists(request.file_path):
            try:
                temp_dir = settings.export_local_path or "/tmp"
                os.makedirs(temp_dir, exist_ok=True)
                local_file_path = os.path.join(
                    temp_dir,
                    f"preview_{authenticated_client_id}_{os.path.basename(request.file_path)}",
                )

                logger.info(f"Downloading file from cloud storage: {request.file_path}")
                await cloud_storage.download_file(request.file_path, local_file_path)
                logger.info(f"Downloaded file to: {local_file_path}")
            except Exception as e:
                logger.error(f"Failed to download file from cloud storage: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File not found or could not be downloaded: {request.file_path}",
                ) from e

        # Convert field mappings to dict
        field_mappings_dict: dict[str, str] = {}
        if request.field_mappings:
            field_mappings_dict = {fm.source: fm.target for fm in request.field_mappings}

        # Get preview with validation
        preview_result = await ImportValidator.preview_with_validation(
            local_file_path,
            request.entity,
            field_mappings_dict,
        )

        # Log response summary
        logger.info(
            f"Import preview completed: client_id={authenticated_client_id}, "
            f"file_path={request.file_path}, entity={request.entity.value}, "
            f"total_records={preview_result['total_records']}, "
            f"valid_count={preview_result['valid_count']}, "
            f"invalid_count={preview_result['invalid_count']}"
        )

        return ImportPreviewResponse(
            file_path=request.file_path,
            entity=request.entity,
            total_records=preview_result["total_records"],
            valid_count=preview_result["valid_count"],
            invalid_count=preview_result["invalid_count"],
            has_action_column=preview_result["has_action_column"],
            records=preview_result["records"],
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    # Generic exceptions are handled by global exception handler for secure error messages


@router.post(
    "/execute",
    summary="Execute import job",
    description="""
    Execute an import job from a previously uploaded and optionally previewed file.

    This endpoint:
    1. Creates an import job definition with optional field mappings
    2. Triggers the import job execution
    3. Returns the job run ID for tracking

    The `file_path` should be obtained from the `/confirm-upload` endpoint.
    Field mappings can be used to rename source columns to target field names.
    """,
    responses={
        201: {
            "description": "Import job created and triggered successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Import job created and triggered",
                        "job_id": "123e4567-e89b-12d3-a456-426614174000",
                        "run_id": "550e8400-e29b-41d4-a716-446655440000",
                    }
                }
            },
        },
        400: {"description": "Invalid request", "model": ErrorResponse},
        404: {"description": "File not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def execute_import(
    request: ImportExecuteRequest,
    authenticated_client_id: UUID = Depends(get_current_client_id),
    job_service: JobService = Depends(get_job_service),
) -> JSONResponse:
    """
    Execute import from a validated file.

    This endpoint:
    1. Creates an import job with the file path and optional field mappings
    2. Starts the import job execution
    3. Returns the job run ID for tracking progress

    Use the `/preview` endpoint first to verify data before executing.
    """
    try:
        from uuid import uuid4

        from app.domain.entities import ImportConfig, JobDefinition, JobType

        # Log request input
        field_mapping_count = len(request.field_mappings) if request.field_mappings else 0
        logger.info(
            f"Execute import request: client_id={authenticated_client_id}, "
            f"file_path={request.file_path}, entity={request.entity.value}, "
            f"field_mappings_count={field_mapping_count}"
        )
        if request.field_mappings:
            mappings = {fm.source: fm.target for fm in request.field_mappings}
            logger.debug(f"Import field mappings: {mappings}")

        # Create import job configuration with field mappings
        import_config = ImportConfig(
            source="cloud_storage",
            entity=request.entity,
            fields=request.field_mappings,  # Pass field mappings to config
            options={
                "source_file": request.file_path,
            },
        )
        job = JobDefinition(
            id=uuid4(),
            client_id=authenticated_client_id,
            name=f"Import {request.entity.value} - {uuid4()}",
            job_type=JobType.IMPORT,
            import_config=import_config,
            enabled=True,
        )
        # Create and run job
        created_job = await job_service.create_job(job)
        # Pass client_id for authorization check
        job_run = await job_service.run_job(created_job.id, client_id=authenticated_client_id)

        # Log response output
        logger.info(
            f"Import job created and started: job_id={created_job.id}, run_id={job_run.id}, "
            f"status={job_run.status.value}, entity={request.entity.value}, "
            f"field_mappings_applied={field_mapping_count > 0}"
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "job_id": str(created_job.id),
                "run_id": str(job_run.id),
                "status": job_run.status.value,
                "message": "Import job created and started",
            },
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        # Convert ValueError to HTTPException for validation errors
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    # Generic exceptions are handled by global exception handler for secure error messages
