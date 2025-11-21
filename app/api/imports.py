"""API routes for import operations."""

import os
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.api.dto import ErrorResponse
from app.auth.backend import get_current_client_id
from app.core.config import get_settings
from app.core.dependency_injection import get_cloud_storage, get_job_service
from app.core.logging import get_logger
from app.domain.entities import ExportEntity
from app.infrastructure.storage.interface import CloudStorageInterface
from app.services.import_validator import ImportValidator
from app.services.job_service import JobService

logger = get_logger(__name__)
router = APIRouter(prefix="/imports", tags=["imports"])
settings = get_settings()


@router.post(
    "/upload",
    summary="Upload and validate import file",
    description="""
    Phase 1: Upload a file, validate its format and content, then store it temporarily in cloud storage.

    This endpoint performs:
    1. File format validation (extension, size, encoding)
    2. Content validation (required fields, data types, malicious input detection)
    3. Temporary storage in cloud storage (if configured)

    If validation succeeds, returns a `file_path` that can be used in Phase 2 (`/execute`).
    If validation fails, returns detailed error information including row and field locations.
    """,
    responses={
        200: {
            "description": "File uploaded and validated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "File validated and uploaded successfully",
                        "file_path": "imports/temp/550e8400-e29b-41d4-a716-446655440000/bills.csv",
                        "record_count": 100,
                    }
                }
            },
        },
        400: {
            "description": "Validation failed",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "message": "Validation failed",
                        "errors": [
                            {
                                "row": 2,
                                "field": "amount",
                                "error": "Field 'amount' must be a valid number",
                            }
                        ],
                    }
                }
            },
            "model": ErrorResponse,
        },
        413: {"description": "File too large", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def upload_import_file(
    file: UploadFile = File(...),
    entity: ExportEntity = Query(default=ExportEntity.BILL, description="Entity type to import"),
    authenticated_client_id: UUID = Depends(get_current_client_id),
    cloud_storage: CloudStorageInterface = Depends(get_cloud_storage),
) -> JSONResponse:
    """
    Upload and validate an import file.
    This is Phase 1 of the import process:
    1. Upload file to temporary location in cloud storage
    2. Download and validate file format and content
    3. Return validation results
    If validation fails, errors include row and field information.
    """
    try:
        # Log request input (excluding file content)
        file_size = file.size if hasattr(file, "size") else "unknown"
        logger.info(
            f"Import file upload request: client_id={authenticated_client_id}, "
            f"filename={file.filename}, content_type={file.content_type}, "
            f"file_size={file_size}, entity={entity.value}"
        )

        # Phase 1: Upload to temporary location
        # Generate temp file path
        # Save uploaded file temporarily
        temp_dir = settings.export_local_path or "/tmp"
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = os.path.join(temp_dir, f"import_{authenticated_client_id}_{file.filename}")
        # Save file locally first for validation
        with open(temp_file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        actual_file_size = len(content)
        logger.info(
            f"File saved for validation: path={temp_file_path}, size={actual_file_size} bytes"
        )

        # Validate file format
        is_valid, format_error = ImportValidator.validate_file_format(temp_file_path)
        if not is_valid:
            logger.warning(
                f"File format validation failed: filename={file.filename}, error={format_error}"
            )
            os.remove(temp_file_path)
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
            temp_file_path, entity
        )
        if not is_valid:
            error_count = len(validation_errors)
            logger.warning(
                f"File content validation failed: filename={file.filename}, "
                f"entity={entity.value}, error_count={error_count}"
            )
            # Clean up temp file
            os.remove(temp_file_path)
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "validation_failed",
                    "message": "File validation failed",
                    "validation_errors": validation_errors,
                    "error_count": error_count,
                },
            )
        # Validation passed - upload to cloud storage
        if cloud_storage:
            # Upload to temp location in cloud storage
            temp_blob_path = f"imports/{authenticated_client_id}/temp/{file.filename}"
            try:
                remote_path = await cloud_storage.upload_file(
                    temp_file_path, temp_blob_path, content_type=file.content_type
                )
                # Clean up local temp file
                os.remove(temp_file_path)
                logger.info(
                    f"Import file validated and uploaded: client_id={authenticated_client_id}, "
                    f"filename={file.filename}, remote_path={remote_path}, entity={entity.value}"
                )
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status": "validated",
                        "message": "File uploaded and validated successfully",
                        "file_path": remote_path,
                        "entity": entity.value,
                        "filename": file.filename,
                    },
                )
            except Exception as e:
                logger.error(
                    f"Failed to upload file to cloud storage: filename={file.filename}, error={str(e)}"
                )
                os.remove(temp_file_path)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload file to cloud storage: {str(e)}",
                ) from e
        else:
            # No cloud storage - keep file locally
            logger.info(
                f"Import file validated (local storage): client_id={authenticated_client_id}, "
                f"filename={file.filename}, path={temp_file_path}, entity={entity.value}"
            )
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "validated",
                    "message": "File validated successfully (stored locally)",
                    "file_path": temp_file_path,
                    "entity": entity.value,
                    "filename": file.filename,
                },
            )
    except HTTPException:
        raise
    except ValueError as e:
        # Convert ValueError to HTTPException for validation errors
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing file upload: {str(e)}",
        ) from e


class ExecuteImportRequest(BaseModel):
    """Request body for executing an import from a validated file."""

    file_path: str = Field(..., description="Path to validated file in cloud storage")
    entity: ExportEntity = Field(..., description="Entity type to import")


@router.post(
    "/execute",
    summary="Execute import job",
    description="""
    Phase 2: Create and execute an import job from a previously validated file.

    This endpoint:
    1. Creates an import job definition
    2. Triggers the import job execution
    3. Returns the job run ID for tracking

    The `file_path` should be obtained from Phase 1 (`/upload`) endpoint.
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
    request: ExecuteImportRequest,
    authenticated_client_id: UUID = Depends(get_current_client_id),
    job_service: JobService = Depends(get_job_service),
) -> JSONResponse:
    """
    Execute import from a validated file.
    This is Phase 2 of the import process:
    1. Create import job with validated file path
    2. Start import job execution
    3. Return job run information
    This should only be called after successful validation via /upload endpoint.
    """
    try:
        from uuid import uuid4

        from app.domain.entities import ImportConfig, JobDefinition, JobType

        # Log request input
        logger.info(
            f"Execute import request: client_id={authenticated_client_id}, "
            f"file_path={request.file_path}, entity={request.entity.value}"
        )

        # Create import job configuration
        import_config = ImportConfig(
            source="cloud_storage",
            entity=request.entity,
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
            f"status={job_run.status.value}, entity={request.entity.value}"
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
    except Exception as e:
        # Convert generic exceptions to HTTPException
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing import: {str(e)}",
        ) from e
    # ApplicationError will be handled by global exception handler
