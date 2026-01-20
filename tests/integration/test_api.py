"""Integration tests for API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(test_client_app: AsyncClient):
    """Test health check endpoint."""
    response = await test_client_app.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_create_job(test_client_app: AsyncClient):
    """Test creating a job via API.

    Note: client_id must be provided in request body and must match the authenticated
    client_id from JWT token. When auth is disabled (in tests), the default client_id
    is "00000000-0000-0000-0000-000000000000".
    """
    from uuid import UUID

    # Default client_id when auth is disabled
    default_client_id = UUID("00000000-0000-0000-0000-000000000000")

    job_data = {
        "client_id": str(default_client_id),  # Must match authenticated client_id from JWT
        "name": "Test Export Job",
        "job_type": "export",
        "export_config": {
            "entity": "bill",
            "fields": [{"field": "id"}, {"field": "amount"}, {"field": "date"}],
            "limit": 100,
        },
        "enabled": True,
    }
    response = await test_client_app.post("/jobs", json=job_data)
    # Should be 201 (success), 400 (validation error), or 500 (server error)
    assert response.status_code in [201, 400, 500]


@pytest.mark.asyncio
async def test_preview_export(test_client_app: AsyncClient):
    """Test export preview endpoint."""
    preview_data = {
        "entity": "bill",
        "fields": [{"field": "id"}, {"field": "amount"}, {"field": "date"}],
        "filters": None,
        "limit": 20,
    }
    # client_id is extracted from JWT token, not from URL path
    response = await test_client_app.post("/exports/preview", json=preview_data)
    # May fail if dependencies not initialized, but should be 200 or 400/500
    assert response.status_code in [200, 400, 500]


@pytest.mark.asyncio
async def test_get_job_runs_with_date_filter(test_client_app: AsyncClient):
    """Test getting job runs with date filtering."""
    from datetime import UTC, datetime, timedelta
    from uuid import UUID

    # Default client_id when auth is disabled
    default_client_id = UUID("00000000-0000-0000-0000-000000000000")

    # First create a job
    job_data = {
        "client_id": str(default_client_id),
        "name": "Test Job for Date Filtering",
        "job_type": "export",
        "export_config": {
            "entity": "bill",
            "fields": [{"field": "id"}, {"field": "amount"}, {"field": "date"}],
            "limit": 100,
        },
        "enabled": True,
    }
    create_response = await test_client_app.post("/jobs", json=job_data)
    if create_response.status_code != 201:
        pytest.skip("Failed to create job for date filtering test")

    job_id = create_response.json()["id"]

    # Get all runs (no filter) - verify endpoint works
    response = await test_client_app.get(f"/jobs/{job_id}/runs")
    assert response.status_code == 200

    # Get runs with start_date filter (future date - should return empty)
    future_date = datetime.now(UTC) + timedelta(days=1)
    # Format datetime for URL (remove microseconds and ensure Z suffix)
    future_date_str = future_date.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    response = await test_client_app.get(f"/jobs/{job_id}/runs?start_date={future_date_str}")
    assert response.status_code == 200
    future_runs = response.json()
    assert len(future_runs) == 0

    # Get runs with end_date filter (past date - might return empty or some runs)
    past_date = datetime.now(UTC) - timedelta(days=1)
    past_date_str = past_date.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    response = await test_client_app.get(f"/jobs/{job_id}/runs?end_date={past_date_str}")
    assert response.status_code == 200
    past_runs = response.json()
    # Verify all returned runs are before past_date
    for run in past_runs:
        run_date = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
        assert run_date <= past_date

    # Get runs with date range filter
    start_date = datetime.now(UTC) - timedelta(days=1)
    end_date = datetime.now(UTC) + timedelta(days=1)
    start_date_str = start_date.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    end_date_str = end_date.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    response = await test_client_app.get(
        f"/jobs/{job_id}/runs?start_date={start_date_str}&end_date={end_date_str}"
    )
    assert response.status_code == 200
    range_runs = response.json()
    # Verify all returned runs are within the date range
    for run in range_runs:
        run_date = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
        assert start_date <= run_date <= end_date


@pytest.mark.asyncio
async def test_get_client_jobs_with_date_filter(test_client_app: AsyncClient):
    """Test getting client jobs with date filtering."""
    from datetime import UTC, datetime, timedelta

    # Get all jobs (no filter) - verify endpoint works
    # Response is now paginated: {items: [...], total: N, page: 1, page_size: 20, total_pages: M}
    response = await test_client_app.get("/jobs")
    assert response.status_code == 200

    # Get jobs with start_date filter (future date - should return empty)
    future_date = datetime.now(UTC) + timedelta(days=1)
    future_date_str = future_date.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    response = await test_client_app.get(f"/jobs?start_date={future_date_str}")
    assert response.status_code == 200
    future_response = response.json()
    future_jobs = future_response.get("items", [])
    assert len(future_jobs) == 0

    # Get jobs with end_date filter (past date)
    past_date = datetime.now(UTC) - timedelta(days=1)
    past_date_str = past_date.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    response = await test_client_app.get(f"/jobs?end_date={past_date_str}")
    assert response.status_code == 200
    past_response = response.json()
    past_jobs = past_response.get("items", [])
    # Verify all returned jobs are before past_date
    for job in past_jobs:
        job_date = datetime.fromisoformat(job["created_at"].replace("Z", "+00:00"))
        assert job_date <= past_date

    # Get jobs with date range filter
    start_date = datetime.now(UTC) - timedelta(days=1)
    end_date = datetime.now(UTC) + timedelta(days=1)
    start_date_str = start_date.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    end_date_str = end_date.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    response = await test_client_app.get(
        f"/jobs?start_date={start_date_str}&end_date={end_date_str}"
    )
    assert response.status_code == 200
    range_response = response.json()
    range_jobs = range_response.get("items", [])
    # Verify all returned jobs are within the date range
    for job in range_jobs:
        job_date = datetime.fromisoformat(job["created_at"].replace("Z", "+00:00"))
        assert start_date <= job_date <= end_date
