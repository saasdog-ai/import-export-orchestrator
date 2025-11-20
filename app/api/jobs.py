"""API routes for job management."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dto import (
    ErrorResponse,
    JobDefinitionCreate,
    JobDefinitionResponse,
    JobDefinitionUpdate,
    JobRunResponse,
)
from app.auth.backend import get_current_client_id
from app.core.dependency_injection import get_job_service
from app.domain.entities import JobDefinition, JobRun
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post(
    "",
    response_model=JobDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}},
)
async def create_job(
    job_data: JobDefinitionCreate,
    authenticated_client_id: UUID = Depends(get_current_client_id),
    job_service: JobService = Depends(get_job_service),
):
    """
    Create a new job definition.
    
    The client_id is extracted from the JWT token. If job_data contains a client_id,
    it must match the authenticated client_id from the token.
    """
    try:
        from app.domain.entities import JobDefinition

        # Use client_id from JWT token (ignore any client_id in request body for security)
        # If request body has client_id, verify it matches (defense in depth)
        if job_data.client_id and job_data.client_id != authenticated_client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Client ID in request does not match authenticated client ID.",
            )

        job = JobDefinition(
            client_id=authenticated_client_id,  # From JWT token - trusted source
            name=job_data.name,
            job_type=job_data.job_type,
            export_config=job_data.export_config,
            import_config=job_data.import_config,
            cron_schedule=job_data.cron_schedule,
            enabled=job_data.enabled,
        )
        created_job = await job_service.create_job(job)
        return JobDefinitionResponse.model_validate(created_job.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/{job_id}",
    response_model=JobDefinitionResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_job(
    job_id: UUID,
    authenticated_client_id: UUID = Depends(get_current_client_id),
    job_service: JobService = Depends(get_job_service),
):
    """Get a job definition by ID."""
    try:
        job = await job_service.get_job(job_id)
        # Verify job belongs to authenticated client
        if job.client_id != authenticated_client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Job does not belong to authenticated client.",
            )
        return JobDefinitionResponse.model_validate(job.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.put(
    "/{job_id}",
    response_model=JobDefinitionResponse,
    responses={404: {"model": ErrorResponse}},
)
async def update_job(
    job_id: UUID,
    job_data: JobDefinitionUpdate,
    authenticated_client_id: UUID = Depends(get_current_client_id),
    job_service: JobService = Depends(get_job_service),
):
    """Update a job definition."""
    try:
        existing_job = await job_service.get_job(job_id)
        # Verify job belongs to authenticated client
        if existing_job.client_id != authenticated_client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Job does not belong to authenticated client.",
            )

        # Merge updates
        update_dict = job_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(existing_job, key, value)

        updated_job = await job_service.update_job(existing_job)
        return JobDefinitionResponse.model_validate(updated_job.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post(
    "/{job_id}/run",
    response_model=JobRunResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}},
)
async def run_job(
    job_id: UUID,
    authenticated_client_id: UUID = Depends(get_current_client_id),
    job_service: JobService = Depends(get_job_service),
):
    """Manually trigger a job run."""
    try:
        job = await job_service.get_job(job_id)
        # Verify job belongs to authenticated client
        if job.client_id != authenticated_client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Job does not belong to authenticated client.",
            )
        job_run = await job_service.run_job(job_id)
        return JobRunResponse.model_validate(job_run.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/{job_id}/runs",
    response_model=List[JobRunResponse],
)
async def get_job_runs(
    job_id: UUID,
    authenticated_client_id: UUID = Depends(get_current_client_id),
    job_service: JobService = Depends(get_job_service),
):
    """Get all runs for a job."""
    try:
        # Verify job exists and belongs to authenticated client
        job = await job_service.get_job(job_id)
        if job.client_id != authenticated_client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Job does not belong to authenticated client.",
            )
        runs = await job_service.get_job_runs(job_id)
        return [JobRunResponse.model_validate(run.model_dump()) for run in runs]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/{job_id}/runs/{run_id}",
    response_model=JobRunResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_job_run(
    job_id: UUID,
    run_id: UUID,
    authenticated_client_id: UUID = Depends(get_current_client_id),
    job_service: JobService = Depends(get_job_service),
):
    """Get a specific job run by ID."""
    try:
        # Verify job exists and belongs to authenticated client
        job = await job_service.get_job(job_id)
        if job.client_id != authenticated_client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Job does not belong to authenticated client.",
            )
        job_run = await job_service.get_job_run(run_id)
        return JobRunResponse.model_validate(job_run.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "",
    response_model=List[JobDefinitionResponse],
)
async def get_client_jobs(
    authenticated_client_id: UUID = Depends(get_current_client_id),
    job_service: JobService = Depends(get_job_service),
):
    """
    Get all jobs for the authenticated client.
    
    The client_id is extracted from the JWT token. This endpoint returns
    all jobs belonging to the authenticated client.
    """
    try:
        jobs = await job_service.get_jobs_by_client(authenticated_client_id)
        return [JobDefinitionResponse.model_validate(job.model_dump()) for job in jobs]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )

