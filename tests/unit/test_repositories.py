"""Unit tests for repositories."""

import pytest

from app.domain.entities import (
    JobDefinition,
    JobRun,
    JobStatus,
)
from app.infrastructure.db.repositories import JobRepository, JobRunRepository


@pytest.mark.asyncio
async def test_create_job(job_repository: JobRepository, test_job: JobDefinition):
    """Test creating a job."""
    created_job = await job_repository.create(test_job)
    assert created_job.id == test_job.id
    assert created_job.name == test_job.name


@pytest.mark.asyncio
async def test_get_job_by_id(job_repository: JobRepository, test_job: JobDefinition):
    """Test getting a job by ID."""
    await job_repository.create(test_job)
    retrieved_job = await job_repository.get_by_id(test_job.id)
    assert retrieved_job is not None
    assert retrieved_job.id == test_job.id


@pytest.mark.asyncio
async def test_get_jobs_by_client(
    job_repository: JobRepository, test_client_id, test_job: JobDefinition
):
    """Test getting jobs by client ID."""
    await job_repository.create(test_job)
    jobs = await job_repository.get_by_client_id(test_client_id)
    assert len(jobs) >= 1
    assert all(job.client_id == test_client_id for job in jobs)


@pytest.mark.asyncio
async def test_create_job_run(
    job_repository: JobRepository,
    job_run_repository: JobRunRepository,
    test_job: JobDefinition,
):
    """Test creating a job run."""
    # First create the job
    created_job = await job_repository.create(test_job)

    job_run = JobRun(
        job_id=created_job.id,
        status=JobStatus.PENDING,
    )
    created_run = await job_run_repository.create(job_run)
    assert created_run.id == job_run.id
    assert created_run.status == JobStatus.PENDING


@pytest.mark.asyncio
async def test_update_job_run_status(
    job_repository: JobRepository,
    job_run_repository: JobRunRepository,
    test_job: JobDefinition,
):
    """Test updating job run status."""
    from datetime import datetime

    # Create job and run
    created_job = await job_repository.create(test_job)

    job_run = JobRun(
        job_id=created_job.id,
        status=JobStatus.PENDING,
    )
    created_run = await job_run_repository.create(job_run)

    # Update status
    updated_run = await job_run_repository.update_status(
        created_run.id,
        JobStatus.RUNNING,
        started_at=datetime.utcnow(),
    )
    assert updated_run.status == JobStatus.RUNNING
    assert updated_run.started_at is not None
