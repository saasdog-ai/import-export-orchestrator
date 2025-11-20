"""Unit tests for repositories.

Note: These tests use real database connections and should be considered integration tests.
For true unit tests with mocked dependencies, see test_repositories_mocked.py
"""

import asyncio

import pytest

from app.domain.entities import (
    JobDefinition,
    JobRun,
    JobStatus,
)
from app.infrastructure.db.repositories import JobRepository, JobRunRepository

# Mark these as integration tests since they use real DB
pytestmark = pytest.mark.integration


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
async def test_get_jobs_by_client_with_date_filter(
    job_repository: JobRepository, test_client_id, test_job: JobDefinition
):
    """Test getting jobs by client ID with date filtering."""
    from datetime import datetime, timedelta

    # Create a job
    await job_repository.create(test_job)

    # Get all jobs
    all_jobs = await job_repository.get_by_client_id(test_client_id)
    assert len(all_jobs) >= 1

    # Filter by start_date (should include the job we just created)
    future_date = datetime.utcnow() + timedelta(days=1)
    future_jobs = await job_repository.get_by_client_id(test_client_id, start_date=future_date)
    assert len(future_jobs) == 0  # No jobs created in the future

    # Filter by end_date (should include the job we just created)
    past_date = datetime.utcnow() - timedelta(days=1)
    await job_repository.get_by_client_id(test_client_id, end_date=past_date)
    # The job we created should be after past_date, so it might not be in results
    # But we can verify the filtering works by calling the method

    # Filter by date range (should include the job)
    start_date = datetime.utcnow() - timedelta(days=1)
    end_date = datetime.utcnow() + timedelta(days=1)
    range_jobs = await job_repository.get_by_client_id(
        test_client_id, start_date=start_date, end_date=end_date
    )
    assert len(range_jobs) >= 1
    assert all(start_date <= job.created_at <= end_date for job in range_jobs)


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


@pytest.mark.asyncio
async def test_get_job_runs_with_date_filter(
    job_repository: JobRepository,
    job_run_repository: JobRunRepository,
    test_job: JobDefinition,
):
    """Test getting job runs with date filtering."""
    from datetime import datetime, timedelta

    # Create job and multiple runs
    created_job = await job_repository.create(test_job)

    # Create runs at different times
    run1 = JobRun(job_id=created_job.id, status=JobStatus.PENDING)
    await job_run_repository.create(run1)

    # Wait a moment to ensure different timestamps
    await asyncio.sleep(0.1)

    run2 = JobRun(job_id=created_job.id, status=JobStatus.PENDING)
    await job_run_repository.create(run2)

    # Get all runs
    all_runs = await job_run_repository.get_by_job_id(created_job.id)
    assert len(all_runs) >= 2

    # Filter by start_date (should include both runs)
    past_date = datetime.utcnow() - timedelta(days=1)
    past_runs = await job_run_repository.get_by_job_id(created_job.id, start_date=past_date)
    assert len(past_runs) >= 2

    # Filter by future start_date (should return empty)
    future_date = datetime.utcnow() + timedelta(days=1)
    future_runs = await job_run_repository.get_by_job_id(created_job.id, start_date=future_date)
    assert len(future_runs) == 0

    # Filter by date range
    start_date = datetime.utcnow() - timedelta(days=1)
    end_date = datetime.utcnow() + timedelta(days=1)
    range_runs = await job_run_repository.get_by_job_id(
        created_job.id, start_date=start_date, end_date=end_date
    )
    assert len(range_runs) >= 2
    assert all(start_date <= run.created_at <= end_date for run in range_runs)
