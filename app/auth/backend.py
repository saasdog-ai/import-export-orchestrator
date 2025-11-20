"""Pluggable authentication backend interface and implementations."""

from uuid import UUID

from fastapi import Request
from fastapi.security import HTTPBearer

from app.core.logging import get_logger

logger = get_logger(__name__)

# Security scheme for FastAPI
security = HTTPBearer(auto_error=False)


class AuthBackendInterface:
    """Interface for authentication backends."""

    def extract_token(self, request: Request) -> str | None:
        """Extract token from request."""
        raise NotImplementedError

    async def validate_token(self, token: str) -> dict | None:
        """Validate JWT token and return payload."""
        raise NotImplementedError

    def verify_issuer(self, payload: dict, expected_issuer: str) -> bool:
        """Verify token issuer."""
        raise NotImplementedError

    def verify_audience(self, payload: dict, expected_audience: str) -> bool:
        """Verify token audience."""
        raise NotImplementedError

    def verify_expiry(self, payload: dict) -> bool:
        """Verify token expiration."""
        raise NotImplementedError

    async def get_current_user_id(self, request: Request) -> UUID | None:
        """Get current authenticated user ID from request."""
        raise NotImplementedError


class JWTAuthBackend(AuthBackendInterface):
    """
    JWT authentication backend.

    TODO: Implement actual JWT validation when security is enabled.
    Currently provides a dummy allow-all implementation.
    """

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        """Initialize JWT auth backend."""
        self.secret_key = secret_key
        self.algorithm = algorithm
        # TODO: Enable real JWT validation
        self.enabled = False

    def extract_token(self, request: Request) -> str | None:
        """
        Extract JWT token from request Authorization header.

        Looks for: Authorization: Bearer <token>
        """
        # TODO: Implement actual token extraction when security is enabled
        # For now, return None to allow all requests
        authorization = request.headers.get("Authorization")
        if not authorization:
            return None

        try:
            scheme, token = authorization.split(" ", 1)
            if scheme.lower() != "bearer":
                return None
            return token
        except ValueError:
            return None

    async def validate_token(self, token: str) -> dict | None:
        """
        Validate JWT token and return decoded payload.

        TODO: Implement actual JWT validation using python-jose when security is enabled.
        """
        if not self.enabled:
            # Dummy allow-all implementation
            logger.debug("JWT validation disabled - allowing request")
            return {"sub": "anonymous", "client_id": "default"}

        # TODO: Implement actual JWT validation
        # from jose import jwt
        # try:
        #     payload = jwt.decode(
        #         token,
        #         self.secret_key,
        #         algorithms=[self.algorithm],
        #     )
        #     return payload
        # except jwt.JWTError as e:
        #     logger.warning(f"JWT validation failed: {e}")
        #     return None

        return None

    def verify_issuer(self, payload: dict, expected_issuer: str) -> bool:
        """Verify token issuer matches expected value."""
        if not self.enabled:
            return True

        # TODO: Implement issuer verification
        # iss = payload.get("iss")
        # return iss == expected_issuer
        return True

    def verify_audience(self, payload: dict, expected_audience: str) -> bool:
        """Verify token audience matches expected value."""
        if not self.enabled:
            return True

        # TODO: Implement audience verification
        # aud = payload.get("aud")
        # return aud == expected_audience or (isinstance(aud, list) and expected_audience in aud)
        return True

    def verify_expiry(self, payload: dict) -> bool:
        """Verify token has not expired."""
        if not self.enabled:
            return True

        # TODO: Implement expiry verification
        # from datetime import datetime, timezone
        # exp = payload.get("exp")
        # if not exp:
        #     return False
        # return datetime.now(timezone.utc).timestamp() < exp
        return True

    async def get_current_user_id(self, request: Request) -> UUID | None:
        """
        Get current authenticated user ID from request.

        TODO: Implement actual user ID extraction when security is enabled.
        Currently returns None to allow all requests.
        """
        if not self.enabled:
            return None

        # TODO: Extract and return user ID from JWT token
        # token = self.extract_token(request)
        # if not token:
        #     return None
        # payload = await self.validate_token(token)
        # if not payload:
        #     return None
        # user_id_str = payload.get("sub")
        # if not user_id_str:
        #     return None
        # try:
        #     return UUID(user_id_str)
        # except ValueError:
        #     return None

        return None

    async def get_current_client_id(self, request: Request) -> UUID | None:
        """
        Get current authenticated client ID from JWT token.

        Extracts client_id from the JWT token payload. The client_id should be
        present as a claim in the token (either as 'client_id' or 'sub' if sub
        represents the client identifier).

        Best Practice: client_id should be in the JWT token, not in URL path parameters,
        to prevent clients from accessing other clients' data by manipulating URLs.
        """
        token = self.extract_token(request)
        if not token:
            if not self.enabled:
                # Return a default client ID for development when auth is disabled
                return UUID("00000000-0000-0000-0000-000000000000")
            return None

        payload = await self.validate_token(token)
        if not payload:
            if not self.enabled:
                # Return a default client ID for development when auth is disabled
                return UUID("00000000-0000-0000-0000-000000000000")
            return None

        # Extract client_id from token payload
        # Try 'client_id' claim first, then 'sub' if it represents the client
        client_id_str = payload.get("client_id") or payload.get("sub")
        if not client_id_str:
            if not self.enabled:
                # Return a default client ID for development when auth is disabled
                return UUID("00000000-0000-0000-0000-000000000000")
            return None

        try:
            return UUID(client_id_str)
        except (ValueError, TypeError):
            if not self.enabled:
                # Return a default client ID for development when auth is disabled
                return UUID("00000000-0000-0000-0000-000000000000")
            return None


# Global auth backend instance (initialized in main.py)
_auth_backend: JWTAuthBackend | None = None


def get_auth_backend() -> JWTAuthBackend:
    """Get the global auth backend instance."""
    global _auth_backend
    if _auth_backend is None:
        from app.core.config import get_settings

        settings = get_settings()
        _auth_backend = JWTAuthBackend(
            secret_key=settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )
    return _auth_backend


async def get_current_client_id(request: Request) -> UUID:
    """
    Dependency function for FastAPI to get current client ID from JWT token.

    Extracts client_id from the validated JWT token. This is the secure way
    to identify the client, as the token is cryptographically signed and cannot
    be tampered with.

    Best Practice: client_id should be in the JWT token (not in URL path),
    preventing clients from accessing other clients' data by changing URLs.
    """
    from fastapi import HTTPException, status

    auth_backend = get_auth_backend()
    client_id = await auth_backend.get_current_client_id(request)

    if client_id is None:
        if auth_backend.enabled:
            # When auth is enabled, require valid token
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated. Valid JWT token with client_id claim required.",
            )
        else:
            # For development, return default client ID when auth is disabled
            return UUID("00000000-0000-0000-0000-000000000000")

    return client_id
