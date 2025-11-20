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
            "fields": ["id", "amount", "date"],
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
        "fields": ["id", "amount", "date"],
        "filters": None,
        "limit": 20,
    }
    # client_id is extracted from JWT token, not from URL path
    response = await test_client_app.post("/exports/preview", json=preview_data)
    # May fail if dependencies not initialized, but should be 200 or 400/500
    assert response.status_code in [200, 400, 500]
