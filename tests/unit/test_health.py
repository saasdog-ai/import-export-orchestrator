"""Unit tests for health check endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.health import health_check, health_check_db


@pytest.mark.asyncio
async def test_health_check():
    """Test basic health check endpoint."""
    result = await health_check()
    assert result.status == "healthy"
    assert result.timestamp is not None


@pytest.mark.asyncio
async def test_health_check_db_success():
    """Test database health check when DB is healthy."""
    # Mock database and session
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = 1
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_db = MagicMock()
    mock_db.async_session_maker.return_value = mock_session
    
    with patch("app.api.health.get_database", return_value=mock_db):
        result = await health_check_db(db=mock_db)
        assert result.status == "healthy"


@pytest.mark.asyncio
async def test_health_check_db_failure():
    """Test database health check when DB connection fails."""
    # Mock database that raises exception
    mock_db = MagicMock()
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=Exception("Connection failed"))
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_db.async_session_maker.return_value = mock_session
    
    from fastapi import HTTPException
    
    with patch("app.api.health.get_database", return_value=mock_db):
        with pytest.raises(HTTPException) as exc_info:
            await health_check_db(db=mock_db)
        assert exc_info.value.status_code == 503

