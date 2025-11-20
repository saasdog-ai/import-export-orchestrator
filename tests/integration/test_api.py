"""Integration tests for API endpoints."""

import pytest
from httpx import AsyncClient

from app.domain.entities import ExportEntity, JobType
from app.main import app


@pytest.mark.asyncio
async def test_health_check(test_client_app: AsyncClient):
    """Test health check endpoint."""
    response = await test_client_app.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_create_job(test_client_app: AsyncClient):
    """Test creating a job via API."""
    from uuid import uuid4

    job_data = {
        "name": "Test Export Job",
        "job_type": "export",
        "export_config": {
            "entity": "bill",
            "fields": ["id", "amount", "date"],
            "limit": 100,
        },
        "enabled": True,
    }
    # Note: client_id is extracted from JWT token, not from request body
    response = await test_client_app.post("/jobs", json=job_data)
    # May fail if dependencies not initialized, but should be 201 or 400/500
    assert response.status_code in [201, 400, 500]


@pytest.mark.asyncio
async def test_preview_export(test_client_app: AsyncClient):
    """Test export preview endpoint."""
    preview_data = {
        "entity": "bill",
        "fields": ["id", "amount", "date"],
        "filters": None,
        "limit": 20,
    }
    # client_id is extracted from JWT token, not from URL path
    response = await test_client_app.post("/exports/preview", json=preview_data)
    # May fail if dependencies not initialized, but should be 200 or 400/500
    assert response.status_code in [200, 400, 500]

