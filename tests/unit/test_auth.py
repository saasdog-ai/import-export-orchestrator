"""Unit tests for authentication backend."""

import pytest
from uuid import UUID

from app.auth.backend import JWTAuthBackend, get_auth_backend
from fastapi import Request


def test_jwt_auth_backend_init():
    """Test JWT auth backend initialization."""
    backend = JWTAuthBackend(secret_key="test-secret", algorithm="HS256")
    assert backend.secret_key == "test-secret"
    assert backend.algorithm == "HS256"
    assert backend.enabled is False  # Disabled by default


def test_extract_token_no_header():
    """Test token extraction with no Authorization header."""
    backend = JWTAuthBackend(secret_key="test-secret")
    request = Request(scope={"type": "http", "headers": []})
    token = backend.extract_token(request)
    assert token is None


def test_extract_token_bearer():
    """Test token extraction with Bearer token."""
    backend = JWTAuthBackend(secret_key="test-secret")
    headers = [(b"authorization", b"Bearer test-token-123")]
    request = Request(scope={"type": "http", "headers": headers})
    token = backend.extract_token(request)
    assert token == "test-token-123"


def test_extract_token_invalid_scheme():
    """Test token extraction with invalid scheme."""
    backend = JWTAuthBackend(secret_key="test-secret")
    headers = [(b"authorization", b"Basic test-token-123")]
    request = Request(scope={"type": "http", "headers": headers})
    token = backend.extract_token(request)
    assert token is None


@pytest.mark.asyncio
async def test_get_current_client_id_disabled():
    """Test getting client ID when auth is disabled."""
    backend = JWTAuthBackend(secret_key="test-secret")
    request = Request(scope={"type": "http", "headers": []})
    client_id = await backend.get_current_client_id(request)
    # Should return default UUID when disabled
    assert client_id is not None
    assert isinstance(client_id, UUID)


@pytest.mark.asyncio
async def test_validate_token_disabled():
    """Test token validation when auth is disabled."""
    backend = JWTAuthBackend(secret_key="test-secret")
    payload = await backend.validate_token("dummy-token")
    # Should return dummy payload when disabled
    assert payload is not None
    assert "sub" in payload or "client_id" in payload


def test_get_auth_backend():
    """Test getting global auth backend instance."""
    backend1 = get_auth_backend()
    backend2 = get_auth_backend()
    # Should return same instance (singleton)
    assert backend1 is backend2

