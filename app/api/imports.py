"""API routes for import operations."""

import os
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse

from app.api.dto import ErrorResponse
from app.auth.backend import get_current_client_id
from app.core.config import get_settings
from app.core.dependency_injection import get_cloud_storage, get_job_service
from app.domain.entities import ExportEntity
from app.infrastructure.storage.interface import CloudStorageInterface
from app.services.import_validator import ImportValidator
from app.services.job_service import JobService

router = APIRouter(prefix="/imports", tags=["imports"])
settings = get_settings()


@router.post(
    "/upload",
    responses={
        200: {"description": "File uploaded and validated successfully"},
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
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

        # Validate file format
        is_valid, format_error = ImportValidator.validate_file_format(temp_file_path)
        if not is_valid:
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
            # Clean up temp file
            os.remove(temp_file_path)
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "validation_failed",
                    "message": "File validation failed",
                    "validation_errors": validation_errors,
                    "error_count": len(validation_errors),
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
                os.remove(temp_file_path)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload file to cloud storage: {str(e) from e}",
                ) from e
        else:
            # No cloud storage - keep file locally
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "validated",
                    "message": "File validated successfully (stored locally)",
                    "file_path": temp_file_path,
                    "entity": entity.value,
                    "filename": file.filename,
                },
            ) from e

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing file upload: {str(e) from e}",
        ) from e


from pydantic import BaseModel, Field


class ExecuteImportRequest(BaseModel):
    """Request body for executing an import from a validated file."""

    file_path: str = Field(..., description="Path to validated file in cloud storage") from e
    entity: ExportEntity = Field(..., description="Entity type to import")


@router.post(
    "/execute",
    responses={
        201: {"description": "Import job created and started"},
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
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
        job_run = await job_service.run_job(created_job.id)

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "job_id": str(created_job.id),
                "run_id": str(job_run.id),
                "status": job_run.status.value,
                "message": "Import job created and started",
            },
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
