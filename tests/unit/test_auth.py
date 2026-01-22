"""Unit tests for authentication backend."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi import Request
from jose import jwt

from app.auth.backend import JWTAuthBackend, get_auth_backend, reset_auth_backend
from app.auth.jwks import JWKSClient, reset_jwks_client
from app.core.constants import DEFAULT_CLIENT_ID

# Test secret key for HS256 tests
TEST_SECRET_KEY = "test-secret-key-for-unit-tests"
TEST_CLIENT_ID = "12345678-1234-1234-1234-123456789abc"


def create_test_token(
    payload: dict,
    secret_key: str = TEST_SECRET_KEY,
    algorithm: str = "HS256",
    expires_delta: timedelta | None = None,
) -> str:
    """Create a test JWT token."""
    to_encode = payload.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(hours=1)
    to_encode["exp"] = expire
    to_encode["iat"] = datetime.now(UTC)
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)


@pytest.fixture
def reset_globals():
    """Reset global instances before and after tests."""
    reset_auth_backend()
    reset_jwks_client()
    yield
    reset_auth_backend()
    reset_jwks_client()


class TestJWTAuthBackendInit:
    """Tests for JWTAuthBackend initialization."""

    def test_init_with_defaults(self):
        """Test JWT auth backend initialization with defaults."""
        backend = JWTAuthBackend(secret_key="test-secret")
        assert backend.secret_key == "test-secret"
        assert backend.algorithm == "RS256"  # Default changed to RS256
        assert backend.enabled is False
        assert backend.issuer is None
        assert backend.audience is None
        assert backend.client_id_claim == "client_id"

    def test_init_with_custom_values(self):
        """Test JWT auth backend initialization with custom values."""
        backend = JWTAuthBackend(
            secret_key="my-secret",
            algorithm="HS256",
            enabled=True,
            issuer="https://auth.example.com/",
            audience="my-api",
            client_id_claim="org_id",
        )
        assert backend.secret_key == "my-secret"
        assert backend.algorithm == "HS256"
        assert backend.enabled is True
        assert backend.issuer == "https://auth.example.com/"
        assert backend.audience == "my-api"
        assert backend.client_id_claim == "org_id"


class TestTokenExtraction:
    """Tests for token extraction from requests."""

    def test_extract_token_no_header(self):
        """Test token extraction with no Authorization header."""
        backend = JWTAuthBackend(secret_key="test-secret")
        request = Request(scope={"type": "http", "headers": []})
        token = backend.extract_token(request)
        assert token is None

    def test_extract_token_bearer(self):
        """Test token extraction with Bearer token."""
        backend = JWTAuthBackend(secret_key="test-secret")
        headers = [(b"authorization", b"Bearer test-token-123")]
        request = Request(scope={"type": "http", "headers": headers})
        token = backend.extract_token(request)
        assert token == "test-token-123"

    def test_extract_token_bearer_lowercase(self):
        """Test token extraction with lowercase bearer."""
        backend = JWTAuthBackend(secret_key="test-secret")
        headers = [(b"authorization", b"bearer test-token-123")]
        request = Request(scope={"type": "http", "headers": headers})
        token = backend.extract_token(request)
        assert token == "test-token-123"

    def test_extract_token_invalid_scheme(self):
        """Test token extraction with invalid scheme."""
        backend = JWTAuthBackend(secret_key="test-secret")
        headers = [(b"authorization", b"Basic test-token-123")]
        request = Request(scope={"type": "http", "headers": headers})
        token = backend.extract_token(request)
        assert token is None

    def test_extract_token_malformed_header(self):
        """Test token extraction with malformed header (no space)."""
        backend = JWTAuthBackend(secret_key="test-secret")
        headers = [(b"authorization", b"BearerNoSpace")]  # No space between scheme and token
        request = Request(scope={"type": "http", "headers": headers})
        token = backend.extract_token(request)
        assert token is None  # Can't split, so returns None


class TestTokenValidationDisabled:
    """Tests for token validation when auth is disabled."""

    @pytest.mark.asyncio
    async def test_validate_token_disabled(self):
        """Test token validation when auth is disabled."""
        backend = JWTAuthBackend(secret_key="test-secret", enabled=False)
        payload = await backend.validate_token("dummy-token")
        assert payload is not None
        assert "sub" in payload
        assert "client_id" in payload

    @pytest.mark.asyncio
    async def test_get_current_client_id_disabled(self):
        """Test getting client ID when auth is disabled."""
        backend = JWTAuthBackend(secret_key="test-secret", enabled=False)
        request = Request(scope={"type": "http", "headers": []})
        client_id = await backend.get_current_client_id(request)
        assert client_id == DEFAULT_CLIENT_ID


class TestTokenValidationHS256:
    """Tests for JWT validation with HS256 (symmetric) algorithm."""

    @pytest.mark.asyncio
    async def test_validate_valid_token(self):
        """Test validation of a valid HS256 token."""
        backend = JWTAuthBackend(
            secret_key=TEST_SECRET_KEY,
            algorithm="HS256",
            enabled=True,
        )
        token = create_test_token(
            {"sub": "user123", "client_id": TEST_CLIENT_ID},
            secret_key=TEST_SECRET_KEY,
            algorithm="HS256",
        )
        payload = await backend.validate_token(token)
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["client_id"] == TEST_CLIENT_ID

    @pytest.mark.asyncio
    async def test_validate_expired_token(self):
        """Test validation of an expired token."""
        backend = JWTAuthBackend(
            secret_key=TEST_SECRET_KEY,
            algorithm="HS256",
            enabled=True,
        )
        token = create_test_token(
            {"sub": "user123", "client_id": TEST_CLIENT_ID},
            secret_key=TEST_SECRET_KEY,
            algorithm="HS256",
            expires_delta=timedelta(hours=-1),  # Expired 1 hour ago
        )
        payload = await backend.validate_token(token)
        assert payload is None

    @pytest.mark.asyncio
    async def test_validate_invalid_signature(self):
        """Test validation of a token with invalid signature."""
        backend = JWTAuthBackend(
            secret_key=TEST_SECRET_KEY,
            algorithm="HS256",
            enabled=True,
        )
        token = create_test_token(
            {"sub": "user123", "client_id": TEST_CLIENT_ID},
            secret_key="wrong-secret-key",  # Different key
            algorithm="HS256",
        )
        payload = await backend.validate_token(token)
        assert payload is None

    @pytest.mark.asyncio
    async def test_validate_malformed_token(self):
        """Test validation of a malformed token."""
        backend = JWTAuthBackend(
            secret_key=TEST_SECRET_KEY,
            algorithm="HS256",
            enabled=True,
        )
        payload = await backend.validate_token("not-a-valid-jwt")
        assert payload is None

    @pytest.mark.asyncio
    async def test_validate_with_issuer(self):
        """Test validation with issuer verification."""
        backend = JWTAuthBackend(
            secret_key=TEST_SECRET_KEY,
            algorithm="HS256",
            enabled=True,
            issuer="https://auth.example.com/",
        )
        token = create_test_token(
            {"sub": "user123", "client_id": TEST_CLIENT_ID, "iss": "https://auth.example.com/"},
            secret_key=TEST_SECRET_KEY,
            algorithm="HS256",
        )
        payload = await backend.validate_token(token)
        assert payload is not None
        assert payload["iss"] == "https://auth.example.com/"

    @pytest.mark.asyncio
    async def test_validate_with_wrong_issuer(self):
        """Test validation with wrong issuer."""
        backend = JWTAuthBackend(
            secret_key=TEST_SECRET_KEY,
            algorithm="HS256",
            enabled=True,
            issuer="https://auth.example.com/",
        )
        token = create_test_token(
            {"sub": "user123", "client_id": TEST_CLIENT_ID, "iss": "https://wrong-issuer.com/"},
            secret_key=TEST_SECRET_KEY,
            algorithm="HS256",
        )
        payload = await backend.validate_token(token)
        assert payload is None

    @pytest.mark.asyncio
    async def test_validate_with_audience(self):
        """Test validation with audience verification."""
        backend = JWTAuthBackend(
            secret_key=TEST_SECRET_KEY,
            algorithm="HS256",
            enabled=True,
            audience="my-api",
        )
        token = create_test_token(
            {"sub": "user123", "client_id": TEST_CLIENT_ID, "aud": "my-api"},
            secret_key=TEST_SECRET_KEY,
            algorithm="HS256",
        )
        payload = await backend.validate_token(token)
        assert payload is not None
        assert payload["aud"] == "my-api"

    @pytest.mark.asyncio
    async def test_validate_with_wrong_audience(self):
        """Test validation with wrong audience."""
        backend = JWTAuthBackend(
            secret_key=TEST_SECRET_KEY,
            algorithm="HS256",
            enabled=True,
            audience="my-api",
        )
        token = create_test_token(
            {"sub": "user123", "client_id": TEST_CLIENT_ID, "aud": "wrong-api"},
            secret_key=TEST_SECRET_KEY,
            algorithm="HS256",
        )
        payload = await backend.validate_token(token)
        assert payload is None


class TestClientIdExtraction:
    """Tests for client ID extraction from tokens."""

    @pytest.mark.asyncio
    async def test_get_client_id_from_client_id_claim(self):
        """Test extracting client_id from 'client_id' claim."""
        backend = JWTAuthBackend(
            secret_key=TEST_SECRET_KEY,
            algorithm="HS256",
            enabled=True,
            client_id_claim="client_id",
        )
        token = create_test_token(
            {"sub": "user123", "client_id": TEST_CLIENT_ID},
            secret_key=TEST_SECRET_KEY,
            algorithm="HS256",
        )
        headers = [(b"authorization", f"Bearer {token}".encode())]
        request = Request(scope={"type": "http", "headers": headers})
        client_id = await backend.get_current_client_id(request)
        assert client_id == UUID(TEST_CLIENT_ID)

    @pytest.mark.asyncio
    async def test_get_client_id_from_custom_claim(self):
        """Test extracting client_id from custom claim."""
        backend = JWTAuthBackend(
            secret_key=TEST_SECRET_KEY,
            algorithm="HS256",
            enabled=True,
            client_id_claim="org_id",
        )
        token = create_test_token(
            {"sub": "user123", "org_id": TEST_CLIENT_ID},
            secret_key=TEST_SECRET_KEY,
            algorithm="HS256",
        )
        headers = [(b"authorization", f"Bearer {token}".encode())]
        request = Request(scope={"type": "http", "headers": headers})
        client_id = await backend.get_current_client_id(request)
        assert client_id == UUID(TEST_CLIENT_ID)

    @pytest.mark.asyncio
    async def test_get_client_id_fallback_to_sub(self):
        """Test fallback to 'sub' claim when client_id claim not found."""
        backend = JWTAuthBackend(
            secret_key=TEST_SECRET_KEY,
            algorithm="HS256",
            enabled=True,
            client_id_claim="client_id",
        )
        token = create_test_token(
            {"sub": TEST_CLIENT_ID},  # No client_id, only sub
            secret_key=TEST_SECRET_KEY,
            algorithm="HS256",
        )
        headers = [(b"authorization", f"Bearer {token}".encode())]
        request = Request(scope={"type": "http", "headers": headers})
        client_id = await backend.get_current_client_id(request)
        assert client_id == UUID(TEST_CLIENT_ID)

    @pytest.mark.asyncio
    async def test_get_client_id_no_token(self):
        """Test client_id extraction with no token (auth enabled)."""
        backend = JWTAuthBackend(
            secret_key=TEST_SECRET_KEY,
            algorithm="HS256",
            enabled=True,
        )
        request = Request(scope={"type": "http", "headers": []})
        client_id = await backend.get_current_client_id(request)
        assert client_id is None

    @pytest.mark.asyncio
    async def test_get_client_id_invalid_uuid(self):
        """Test client_id extraction with invalid UUID format."""
        backend = JWTAuthBackend(
            secret_key=TEST_SECRET_KEY,
            algorithm="HS256",
            enabled=True,
        )
        token = create_test_token(
            {"sub": "not-a-uuid", "client_id": "also-not-a-uuid"},
            secret_key=TEST_SECRET_KEY,
            algorithm="HS256",
        )
        headers = [(b"authorization", f"Bearer {token}".encode())]
        request = Request(scope={"type": "http", "headers": headers})
        client_id = await backend.get_current_client_id(request)
        assert client_id is None


class TestVerificationMethods:
    """Tests for individual verification methods."""

    def test_verify_issuer_disabled(self):
        """Test issuer verification when auth is disabled."""
        backend = JWTAuthBackend(secret_key="test", enabled=False)
        assert backend.verify_issuer({}, "any-issuer") is True

    def test_verify_issuer_valid(self):
        """Test issuer verification with valid issuer."""
        backend = JWTAuthBackend(secret_key="test", enabled=True)
        assert backend.verify_issuer({"iss": "expected"}, "expected") is True

    def test_verify_issuer_invalid(self):
        """Test issuer verification with invalid issuer."""
        backend = JWTAuthBackend(secret_key="test", enabled=True)
        assert backend.verify_issuer({"iss": "wrong"}, "expected") is False

    def test_verify_audience_disabled(self):
        """Test audience verification when auth is disabled."""
        backend = JWTAuthBackend(secret_key="test", enabled=False)
        assert backend.verify_audience({}, "any-audience") is True

    def test_verify_audience_valid_string(self):
        """Test audience verification with valid string audience."""
        backend = JWTAuthBackend(secret_key="test", enabled=True)
        assert backend.verify_audience({"aud": "expected"}, "expected") is True

    def test_verify_audience_valid_list(self):
        """Test audience verification with valid list audience."""
        backend = JWTAuthBackend(secret_key="test", enabled=True)
        assert backend.verify_audience({"aud": ["api1", "api2"]}, "api2") is True

    def test_verify_audience_invalid(self):
        """Test audience verification with invalid audience."""
        backend = JWTAuthBackend(secret_key="test", enabled=True)
        assert backend.verify_audience({"aud": "wrong"}, "expected") is False

    def test_verify_expiry_disabled(self):
        """Test expiry verification when auth is disabled."""
        backend = JWTAuthBackend(secret_key="test", enabled=False)
        assert backend.verify_expiry({}) is True

    def test_verify_expiry_valid(self):
        """Test expiry verification with valid (future) expiry."""
        backend = JWTAuthBackend(secret_key="test", enabled=True)
        future_exp = datetime.now(UTC) + timedelta(hours=1)
        assert backend.verify_expiry({"exp": future_exp.timestamp()}) is True

    def test_verify_expiry_expired(self):
        """Test expiry verification with expired token."""
        backend = JWTAuthBackend(secret_key="test", enabled=True)
        past_exp = datetime.now(UTC) - timedelta(hours=1)
        assert backend.verify_expiry({"exp": past_exp.timestamp()}) is False

    def test_verify_expiry_no_exp(self):
        """Test expiry verification with no exp claim."""
        backend = JWTAuthBackend(secret_key="test", enabled=True)
        assert backend.verify_expiry({}) is False


class TestGlobalBackend:
    """Tests for global auth backend singleton."""

    def test_get_auth_backend_singleton(self, reset_globals):
        """Test getting global auth backend instance."""
        backend1 = get_auth_backend()
        backend2 = get_auth_backend()
        assert backend1 is backend2

    def test_reset_auth_backend(self, reset_globals):
        """Test resetting global auth backend."""
        backend1 = get_auth_backend()
        reset_auth_backend()
        backend2 = get_auth_backend()
        assert backend1 is not backend2


class TestJWKSClient:
    """Tests for JWKS client."""

    @pytest.mark.asyncio
    async def test_jwks_client_init(self):
        """Test JWKS client initialization."""
        client = JWKSClient(
            jwks_url="https://auth.example.com/.well-known/jwks.json",
            cache_ttl=1800,
        )
        assert client.jwks_url == "https://auth.example.com/.well-known/jwks.json"
        assert client.cache_ttl == 1800
        assert client._keys == {}

    @pytest.mark.asyncio
    async def test_jwks_client_cache_invalid_initially(self):
        """Test that cache is invalid when empty."""
        client = JWKSClient(jwks_url="https://example.com/jwks.json")
        assert client._is_cache_valid() is False

    @pytest.mark.asyncio
    async def test_jwks_client_fetch_success(self):
        """Test successful JWKS fetch."""
        client = JWKSClient(jwks_url="https://example.com/jwks.json")

        mock_jwks = {
            "keys": [
                {
                    "kty": "RSA",
                    "kid": "key1",
                    "use": "sig",
                    "n": "0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx4cbbfAAtVT86zwu1RK7aPFFxuhDR1L6tSoc_BJECPebWKRXjBZCiFV4n3oknjhMstn64tZ_2W-5JsGY4Hc5n9yBXArwl93lqt7_RN5w6Cf0h4QyQ5v-65YGjQR0_FDW2QvzqY368QQMicAtaSqzs8KJZgnYb9c7d0zgdAZHzu6qMQvRL5hajrn1n91CbOpbISD08qNLyrdkt-bFTWhAI4vMQFh6WeZu0fM4lFd2NcRwr3XPksINHaQ-G_xBniIqbw0Ls1jF44-csFCur-kEgU8awapJzKnqDKgw",
                    "e": "AQAB",
                    "alg": "RS256",
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_jwks
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            mock_client_class.return_value = mock_client

            keys = await client.get_keys()
            assert "key1" in keys

    @pytest.mark.asyncio
    async def test_jwks_client_get_signing_key_no_kid(self):
        """Test getting signing key when token has no kid."""
        client = JWKSClient(jwks_url="https://example.com/jwks.json")

        # Mock a single-key JWKS
        mock_key = MagicMock()
        client._keys = {"only-key": mock_key}
        client._last_fetch = datetime.now(UTC).timestamp()

        key = await client.get_signing_key({})  # No kid in headers
        assert key == mock_key

    @pytest.mark.asyncio
    async def test_jwks_client_get_signing_key_with_kid(self):
        """Test getting signing key with kid."""
        client = JWKSClient(jwks_url="https://example.com/jwks.json")

        mock_key = MagicMock()
        client._keys = {"my-kid": mock_key, "other-kid": MagicMock()}
        client._last_fetch = datetime.now(UTC).timestamp()

        key = await client.get_signing_key({"kid": "my-kid"})
        assert key == mock_key
