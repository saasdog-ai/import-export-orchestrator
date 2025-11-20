"""Unit tests for services."""

import pytest
from uuid import uuid4

from app.domain.entities import (
    ExportConfig,
    ExportEntity,
    JobDefinition,
    JobRun,
    JobStatus,
    JobType,
)
from app.services.job_service import JobService


@pytest.mark.asyncio
async def test_create_job(job_service: JobService, test_client_id):
    """Test creating a job via service."""
    export_config = ExportConfig(
        entity=ExportEntity.BILL,
        fields=["id", "amount", "date"],
        limit=100,
    )
    job = JobDefinition(
        id=uuid4(),
        client_id=test_client_id,
        name="Test Export Job",
        job_type=JobType.EXPORT,
        export_config=export_config,
        enabled=True,
    )
    created_job = await job_service.create_job(job)
    assert created_job.id == job.id
    assert created_job.name == job.name
    assert created_job.client_id == test_client_id


@pytest.mark.asyncio
async def test_get_job(job_service: JobService, test_job: JobDefinition):
    """Test getting a job by ID."""
    created_job = await job_service.create_job(test_job)
    retrieved_job = await job_service.get_job(created_job.id)
    assert retrieved_job is not None
    assert retrieved_job.id == created_job.id
    assert retrieved_job.name == created_job.name


@pytest.mark.asyncio
async def test_get_jobs_by_client(job_service: JobService, test_client_id, test_job: JobDefinition):
    """Test getting jobs by client ID."""
    await job_service.create_job(test_job)
    jobs = await job_service.get_jobs_by_client(test_client_id)
    assert len(jobs) >= 1
    assert all(job.client_id == test_client_id for job in jobs)


@pytest.mark.asyncio
async def test_run_job(job_service: JobService, test_job: JobDefinition):
    """Test running a job."""
    created_job = await job_service.create_job(test_job)
    job_run = await job_service.run_job(created_job.id)
    assert job_run is not None
    assert job_run.job_id == created_job.id
    assert job_run.status == JobStatus.PENDING


@pytest.mark.asyncio
async def test_get_job_runs(job_service: JobService, test_job: JobDefinition):
    """Test getting job runs."""
    created_job = await job_service.create_job(test_job)
    await job_service.run_job(created_job.id)
    runs = await job_service.get_job_runs(created_job.id)
    assert len(runs) >= 1
    assert all(run.job_id == created_job.id for run in runs)

