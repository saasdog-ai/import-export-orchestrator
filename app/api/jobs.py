"""API routes for job management."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dto import (
    ErrorResponse,
    JobDefinitionClone,
    JobDefinitionCreate,
    JobDefinitionResponse,
    JobDefinitionUpdate,
    JobRunResponse,
    JobRunSummary,
    PaginatedJobsResponse,
)
from app.auth.backend import get_current_client_id
from app.core.dependency_injection import get_job_service
from app.core.logging import get_logger
from app.services.job_service import JobService

logger = get_logger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post(
    "",
    response_model=JobDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create job definition",
    description="Create a new import or export job definition with optional scheduling.",
    responses={
        201: {
            "description": "Job definition created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "client_id": "00000000-0000-0000-0000-000000000000",
                        "name": "Daily Bill Export",
                        "job_type": "export",
                        "export_config": {
                            "entity": "bill",
                            "fields": ["id", "amount", "date"],
                            "filters": None,
                            "sort": None,
                            "limit": 100,
                            "offset": 0,
                        },
                        "import_config": None,
                        "cron_schedule": "0 0 * * *",
                        "enabled": True,
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                    }
                }
            },
        },
        400: {"description": "Invalid request data", "model": ErrorResponse},
        403: {"description": "Client ID mismatch", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
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

    **Request Body:**
    - `name`: Job name (required)
    - `job_type`: Either "import" or "export" (required)
    - `export_config`: Export configuration (required for export jobs)
    - `import_config`: Import configuration (required for import jobs)
    - `cron_schedule`: Optional cron expression for scheduled execution
    - `enabled`: Whether the job is enabled (default: true)

    **Example Request:**
    ```json
    {
        "name": "Daily Bill Export",
        "job_type": "export",
        "export_config": {
            "entity": "bill",
            "fields": ["id", "amount", "date"],
            "limit": 100
        },
        "cron_schedule": "0 0 * * *",
        "enabled": true
    }
    ```
    """
    try:
        from app.domain.entities import JobDefinition

        # Log request input (excluding PII)
        logger.info(
            f"Create job request: client_id={authenticated_client_id}, "
            f"name={job_data.name}, job_type={job_data.job_type.value}, "
            f"has_export_config={'yes' if job_data.export_config else 'no'}, "
            f"has_import_config={'yes' if job_data.import_config else 'no'}, "
            f"cron_schedule={'present' if job_data.cron_schedule else 'none'}, "
            f"enabled={job_data.enabled}"
        )

        # Use client_id from JWT token (ignore any client_id in request body for security)
        # If request body has client_id, verify it matches (defense in depth)
        if job_data.client_id and job_data.client_id != authenticated_client_id:
            logger.warning(
                f"Client ID mismatch: request_client_id={job_data.client_id}, "
                f"authenticated_client_id={authenticated_client_id}"
            )
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

        # Log response output
        logger.info(
            f"Job created: job_id={created_job.id}, client_id={authenticated_client_id}, "
            f"job_type={created_job.job_type.value}, name={created_job.name}"
        )

        return JobDefinitionResponse.model_validate(created_job.model_dump())
    except HTTPException:
        # Re-raise HTTP exceptions (e.g., from client ID mismatch check)
        raise
    # ApplicationError will be handled by global exception handler


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
        # Log request input
        logger.info(f"Get job request: job_id={job_id}, client_id={authenticated_client_id}")

        job = await job_service.get_job(job_id)
        # Verify job belongs to authenticated client
        if job.client_id != authenticated_client_id:
            logger.warning(
                f"Access denied: job_id={job_id}, requested_client_id={authenticated_client_id}, "
                f"job_client_id={job.client_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Job does not belong to authenticated client.",
            )

        # Log response output
        logger.info(
            f"Job retrieved: job_id={job_id}, job_type={job.job_type.value}, "
            f"name={job.name}, enabled={job.enabled}"
        )

        return JobDefinitionResponse.model_validate(job.model_dump())
    except HTTPException:
        # Re-raise HTTP exceptions (e.g., from access denied check)
        raise
    # ApplicationError (e.g., NotFoundError) will be handled by global exception handler


@router.put(
    "/{job_id}",
    response_model=JobDefinitionResponse,
    summary="Update job definition (safe fields only)",
    description="""Update an existing job definition. Only 'safe' fields can be updated:
    - name: Job name
    - cron_schedule: Cron expression for scheduling
    - enabled: Whether the job is enabled

    Config fields (export_config, import_config) are immutable. To modify config,
    use the clone endpoint to create a new job with the desired configuration.""",
    responses={
        200: {
            "description": "Job definition updated successfully",
        },
        403: {"description": "Access denied", "model": ErrorResponse},
        404: {"description": "Job not found", "model": ErrorResponse},
    },
)
async def update_job(
    job_id: UUID,
    job_data: JobDefinitionUpdate,
    authenticated_client_id: UUID = Depends(get_current_client_id),
    job_service: JobService = Depends(get_job_service),
):
    """Update a job definition (safe fields only: name, cron_schedule, enabled)."""
    try:
        # Log request input
        update_fields = list(job_data.model_dump(exclude_unset=True).keys())
        logger.info(
            f"Update job request: job_id={job_id}, client_id={authenticated_client_id}, "
            f"fields_to_update={update_fields}"
        )

        existing_job = await job_service.get_job(job_id)
        # Verify job belongs to authenticated client
        if existing_job.client_id != authenticated_client_id:
            logger.warning(
                f"Access denied for update: job_id={job_id}, "
                f"requested_client_id={authenticated_client_id}, job_client_id={existing_job.client_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Job does not belong to authenticated client.",
            )

        # Merge updates
        update_dict = job_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(existing_job, key, value)

        updated_job = await job_service.update_job(existing_job)

        # Log response output
        logger.info(
            f"Job updated: job_id={job_id}, updated_fields={update_fields}, "
            f"enabled={updated_job.enabled}"
        )

        return JobDefinitionResponse.model_validate(updated_job.model_dump())
    except HTTPException:
        # Re-raise HTTP exceptions (e.g., from access denied check)
        raise
    # ApplicationError (e.g., NotFoundError) will be handled by global exception handler


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete job definition",
    description="Delete a job definition and all its runs. Only the owner can delete their jobs.",
    responses={
        204: {"description": "Job deleted successfully"},
        403: {"description": "Access denied", "model": ErrorResponse},
        404: {"description": "Job not found", "model": ErrorResponse},
    },
)
async def delete_job(
    job_id: UUID,
    authenticated_client_id: UUID = Depends(get_current_client_id),
    job_service: JobService = Depends(get_job_service),
):
    """Delete a job definition and all its associated runs."""
    try:
        logger.info(f"Delete job request: job_id={job_id}, client_id={authenticated_client_id}")

        await job_service.delete_job(job_id, client_id=authenticated_client_id)

        logger.info(f"Job deleted: job_id={job_id}, client_id={authenticated_client_id}")
        return None
    except HTTPException:
        raise
    # ApplicationError (e.g., NotFoundError, ForbiddenError) will be handled by global exception handler


@router.post(
    "/{job_id}/clone",
    response_model=JobDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Clone job definition",
    description="""Clone an existing job to create a new one with optional modifications.

    Use this endpoint to create a modified version of a job when you need to change
    config fields (export_config, import_config) which are immutable on existing jobs.

    The new job will have:
    - A new ID
    - The specified name (required)
    - Config from the source job, unless overridden
    - No run history (it's a new job)""",
    responses={
        201: {"description": "Job cloned successfully"},
        403: {"description": "Access denied", "model": ErrorResponse},
        404: {"description": "Source job not found", "model": ErrorResponse},
    },
)
async def clone_job(
    job_id: UUID,
    clone_data: JobDefinitionClone,
    authenticated_client_id: UUID = Depends(get_current_client_id),
    job_service: JobService = Depends(get_job_service),
):
    """Clone a job definition to create a new job with optional config modifications."""
    try:
        logger.info(
            f"Clone job request: source_job_id={job_id}, client_id={authenticated_client_id}, "
            f"new_name={clone_data.name}"
        )

        # Get source job
        source_job = await job_service.get_job(job_id)

        # Verify job belongs to authenticated client
        if source_job.client_id != authenticated_client_id:
            logger.warning(
                f"Access denied for clone: job_id={job_id}, "
                f"requested_client_id={authenticated_client_id}, job_client_id={source_job.client_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Job does not belong to authenticated client.",
            )

        # Create new job definition based on source
        from app.domain.entities import JobDefinition

        new_job = JobDefinition(
            client_id=authenticated_client_id,
            name=clone_data.name,
            job_type=source_job.job_type,
            export_config=clone_data.export_config or source_job.export_config,
            import_config=clone_data.import_config or source_job.import_config,
            cron_schedule=clone_data.cron_schedule
            if clone_data.cron_schedule is not None
            else source_job.cron_schedule,
            enabled=clone_data.enabled,
        )

        created_job = await job_service.create_job(new_job)

        logger.info(
            f"Job cloned: source_job_id={job_id}, new_job_id={created_job.id}, "
            f"new_name={created_job.name}"
        )

        return JobDefinitionResponse.model_validate(created_job.model_dump())
    except HTTPException:
        raise
    # ApplicationError (e.g., NotFoundError) will be handled by global exception handler


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
        # Log request input
        logger.info(f"Run job request: job_id={job_id}, client_id={authenticated_client_id}")

        job = await job_service.get_job(job_id)
        # Verify job belongs to authenticated client
        if job.client_id != authenticated_client_id:
            logger.warning(
                f"Access denied for run: job_id={job_id}, "
                f"requested_client_id={authenticated_client_id}, job_client_id={job.client_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Job does not belong to authenticated client.",
            )
        # Pass client_id for authorization check in service layer
        job_run = await job_service.run_job(job_id, client_id=authenticated_client_id)

        # Log response output
        logger.info(
            f"Job run triggered: job_id={job_id}, run_id={job_run.id}, "
            f"status={job_run.status.value}"
        )

        return JobRunResponse.model_validate(job_run.model_dump())
    except HTTPException:
        # Re-raise HTTP exceptions (e.g., from access denied check)
        raise
    # ApplicationError (e.g., NotFoundError) will be handled by global exception handler


@router.get(
    "/{job_id}/runs",
    response_model=list[JobRunResponse],
    summary="Get job runs",
    description="Retrieve all runs for a specific job, optionally filtered by date range.",
    responses={
        200: {
            "description": "List of job runs",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "job_id": "123e4567-e89b-12d3-a456-426614174000",
                            "status": "succeeded",
                            "started_at": "2024-01-01T12:00:00Z",
                            "completed_at": "2024-01-01T12:05:00Z",
                            "error_message": None,
                            "result_metadata": {"records_exported": 100},
                            "created_at": "2024-01-01T12:00:00Z",
                            "updated_at": "2024-01-01T12:05:00Z",
                        }
                    ]
                }
            },
        },
        403: {"description": "Access denied. Job does not belong to authenticated client."},
        404: {"description": "Job not found."},
        500: {"description": "Internal server error."},
    },
)
async def get_job_runs(
    job_id: UUID,
    start_date: Annotated[
        datetime | None,
        Query(
            description="Filter runs created after this date/time (ISO 8601 format, e.g., 2024-01-01T00:00:00Z)"
        ),
    ] = None,
    end_date: Annotated[
        datetime | None,
        Query(
            description="Filter runs created before this date/time (ISO 8601 format, e.g., 2024-12-31T23:59:59Z)"
        ),
    ] = None,
    authenticated_client_id: UUID = Depends(get_current_client_id),
    job_service: JobService = Depends(get_job_service),
):
    """
    Get all runs for a job, optionally filtered by date range.

    Query Parameters:
    - start_date: Filter runs created after this date/time (ISO 8601 format)
    - end_date: Filter runs created before this date/time (ISO 8601 format)

    Examples:
    - Get all runs: GET /jobs/{job_id}/runs
    - Get runs after a date: GET /jobs/{job_id}/runs?start_date=2024-01-01T00:00:00Z
    - Get runs in a date range: GET /jobs/{job_id}/runs?start_date=2024-01-01T00:00:00Z&end_date=2024-12-31T23:59:59Z
    """
    try:
        # Log request input
        logger.info(
            f"Get job runs request: job_id={job_id}, client_id={authenticated_client_id}, "
            f"start_date={start_date}, end_date={end_date}"
        )

        # Verify job exists and belongs to authenticated client
        job = await job_service.get_job(job_id)
        if job.client_id != authenticated_client_id:
            logger.warning(
                f"Access denied: job_id={job_id}, requested_client_id={authenticated_client_id}, "
                f"job_client_id={job.client_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Job does not belong to authenticated client.",
            )
        # Convert timezone-aware datetimes to naive UTC if needed
        # FastAPI parses ISO 8601 strings and may return timezone-aware datetimes
        if start_date and start_date.tzinfo is not None:
            # Convert to UTC first, then remove timezone info
            start_date = start_date.astimezone(UTC).replace(tzinfo=None)
        if end_date and end_date.tzinfo is not None:
            # Convert to UTC first, then remove timezone info
            end_date = end_date.astimezone(UTC).replace(tzinfo=None)
        runs = await job_service.get_job_runs(job_id, start_date=start_date, end_date=end_date)

        # Log response output
        logger.info(f"Job runs retrieved: job_id={job_id}, run_count={len(runs)}")

        return [JobRunResponse.model_validate(run.model_dump()) for run in runs]
    except HTTPException:
        # Re-raise HTTP exceptions (e.g., from access denied check)
        raise
    # ApplicationError (e.g., NotFoundError) will be handled by global exception handler


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
        # Log request input
        logger.info(
            f"Get job run request: job_id={job_id}, run_id={run_id}, client_id={authenticated_client_id}"
        )

        # Verify job exists and belongs to authenticated client
        job = await job_service.get_job(job_id)
        if job.client_id != authenticated_client_id:
            logger.warning(
                f"Access denied: job_id={job_id}, run_id={run_id}, "
                f"requested_client_id={authenticated_client_id}, job_client_id={job.client_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Job does not belong to authenticated client.",
            )
        job_run = await job_service.get_job_run(run_id)

        # Log response output
        logger.info(
            f"Job run retrieved: run_id={run_id}, status={job_run.status.value}, "
            f"started_at={job_run.started_at}, completed_at={job_run.completed_at}"
        )

        return JobRunResponse.model_validate(job_run.model_dump())
    except HTTPException:
        # Re-raise HTTP exceptions (e.g., from access denied check)
        raise
    # ApplicationError (e.g., NotFoundError) will be handled by global exception handler


@router.get(
    "",
    response_model=PaginatedJobsResponse,
    summary="Get client jobs",
    description="Get job definitions for the authenticated client with pagination and filtering.",
    responses={
        200: {
            "description": "Paginated list of job definitions",
        },
    },
)
async def get_client_jobs(
    page: Annotated[
        int,
        Query(ge=1, description="Page number (1-indexed)"),
    ] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100, description="Number of items per page (max 100)"),
    ] = 20,
    job_type: Annotated[
        str | None,
        Query(description="Filter by job type (export or import)"),
    ] = None,
    entity: Annotated[
        str | None,
        Query(description="Filter by entity type (bill, invoice, vendor, project)"),
    ] = None,
    start_date: Annotated[
        datetime | None,
        Query(description="Filter jobs created after this date/time (ISO 8601 format)"),
    ] = None,
    end_date: Annotated[
        datetime | None,
        Query(description="Filter jobs created before this date/time (ISO 8601 format)"),
    ] = None,
    authenticated_client_id: UUID = Depends(get_current_client_id),
    job_service: JobService = Depends(get_job_service),
):
    """
    Get jobs for the authenticated client with pagination and filtering.

    The client_id is extracted from the JWT token. This endpoint returns
    only jobs belonging to the authenticated client.

    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    - job_type: Filter by job type (export or import)
    - entity: Filter by entity type (bill, invoice, vendor, project)
    - start_date: Filter jobs created after this date/time
    - end_date: Filter jobs created before this date/time

    Examples:
    - Get first page: GET /jobs
    - Get second page: GET /jobs?page=2
    - Filter by type: GET /jobs?job_type=export
    - Filter by entity: GET /jobs?entity=bill
    - Combined filters: GET /jobs?job_type=export&entity=bill&page_size=50
    """
    # Log request input
    logger.info(
        f"Get client jobs request: client_id={authenticated_client_id}, "
        f"page={page}, page_size={page_size}, job_type={job_type}, entity={entity}, "
        f"start_date={start_date}, end_date={end_date}"
    )

    # Convert timezone-aware datetimes to naive UTC if needed
    if start_date and start_date.tzinfo is not None:
        start_date = start_date.astimezone(UTC).replace(tzinfo=None)
    if end_date and end_date.tzinfo is not None:
        end_date = end_date.astimezone(UTC).replace(tzinfo=None)

    jobs, total_count = await job_service.get_jobs_by_client(
        authenticated_client_id,
        start_date=start_date,
        end_date=end_date,
        job_type=job_type,
        entity=entity,
        page=page,
        page_size=page_size,
    )

    # Fetch last run for each job
    job_responses = []
    for job in jobs:
        job_data = job.model_dump()
        # Get the most recent run for this job
        runs = await job_service.get_job_runs(job.id)
        if runs:
            # Sort by created_at descending to get the latest run
            latest_run = max(runs, key=lambda r: r.created_at)
            job_data["last_run"] = JobRunSummary(
                id=latest_run.id,
                status=latest_run.status,
                started_at=latest_run.started_at,
                completed_at=latest_run.completed_at,
                error_message=latest_run.error_message,
            )
        else:
            job_data["last_run"] = None
        job_responses.append(JobDefinitionResponse.model_validate(job_data))

    # Calculate total pages
    total_pages = (total_count + page_size - 1) // page_size

    # Log response output
    logger.info(
        f"Client jobs retrieved: client_id={authenticated_client_id}, "
        f"page={page}/{total_pages}, items={len(jobs)}, total={total_count}"
    )

    return PaginatedJobsResponse(
        items=job_responses,
        total=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
