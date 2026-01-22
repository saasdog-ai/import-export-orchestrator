"""Pluggable authentication backend interface and implementations."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from fastapi.security import HTTPBearer
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError

from app.core.constants import DEFAULT_CLIENT_ID
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
    JWT authentication backend with JWKS support.

    Supports two modes:
    1. JWKS (asymmetric): Fetches public keys from a JWKS endpoint for RS256/ES256
    2. Secret key (symmetric): Uses a shared secret for HS256

    When enabled=False (development mode), allows all requests with a default client ID.
    """

    def __init__(
        self,
        secret_key: str | None = None,
        algorithm: str = "RS256",
        enabled: bool = False,
        issuer: str | None = None,
        audience: str | None = None,
        client_id_claim: str = "client_id",
    ):
        """
        Initialize JWT auth backend.

        Args:
            secret_key: Secret key for HS256 algorithm (not used with JWKS)
            algorithm: JWT signing algorithm (RS256, ES256, HS256, etc.)
            enabled: Whether authentication is enabled
            issuer: Expected issuer claim (optional)
            audience: Expected audience claim (optional)
            client_id_claim: Claim name containing the client ID
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.enabled = enabled
        self.issuer = issuer
        self.audience = audience
        self.client_id_claim = client_id_claim

    def extract_token(self, request: Request) -> str | None:
        """
        Extract JWT token from request Authorization header.

        Looks for: Authorization: Bearer <token>
        """
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

        For asymmetric algorithms (RS256, ES256), uses JWKS to get the public key.
        For symmetric algorithms (HS256), uses the configured secret key.
        """
        if not self.enabled:
            # Development mode - allow all requests
            logger.debug("JWT validation disabled - allowing request")
            return {"sub": "anonymous", "client_id": "default"}

        try:
            # Get unverified headers to determine the key
            unverified_headers = jwt.get_unverified_headers(token)
            algorithm = unverified_headers.get("alg", self.algorithm)

            # Build validation options
            options = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "require_exp": True,
            }

            # Add issuer verification if configured
            if self.issuer:
                options["verify_iss"] = True

            # Add audience verification if configured
            if self.audience:
                options["verify_aud"] = True

            # Get the key for verification
            key = await self._get_verification_key(unverified_headers, algorithm)
            if key is None:
                logger.warning("No verification key available for JWT validation")
                return None

            # Decode and validate the token
            payload = jwt.decode(
                token,
                key,
                algorithms=[algorithm],
                issuer=self.issuer,
                audience=self.audience,
                options=options,
            )

            logger.debug(
                f"JWT validated successfully for client: {payload.get(self.client_id_claim)}"
            )
            return payload

        except ExpiredSignatureError:
            logger.warning("JWT token has expired")
            return None
        except JWTClaimsError as e:
            logger.warning(f"JWT claims verification failed: {e}")
            return None
        except JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during JWT validation: {e}")
            return None

    async def _get_verification_key(self, headers: dict, algorithm: str) -> str | bytes | None:
        """
        Get the key for JWT verification.

        For asymmetric algorithms, fetches from JWKS.
        For symmetric algorithms, returns the configured secret key.
        """
        if algorithm.startswith("HS"):
            # Symmetric algorithm - use secret key
            if not self.secret_key:
                logger.error("No secret key configured for HS256 algorithm")
                return None
            return self.secret_key

        # Asymmetric algorithm - use JWKS
        from app.auth.jwks import get_jwks_client

        jwks_client = get_jwks_client()
        if jwks_client is None:
            logger.error("JWKS client not configured for asymmetric algorithm")
            return None

        signing_key = await jwks_client.get_signing_key(headers)
        if signing_key is None:
            logger.warning(f"No signing key found for kid={headers.get('kid')}")
            return None

        return signing_key

    def verify_issuer(self, payload: dict, expected_issuer: str) -> bool:
        """Verify token issuer matches expected value."""
        if not self.enabled:
            return True

        iss = payload.get("iss")
        return iss == expected_issuer

    def verify_audience(self, payload: dict, expected_audience: str) -> bool:
        """Verify token audience matches expected value."""
        if not self.enabled:
            return True

        aud = payload.get("aud")
        if isinstance(aud, list):
            return expected_audience in aud
        return aud == expected_audience

    def verify_expiry(self, payload: dict) -> bool:
        """Verify token has not expired."""
        if not self.enabled:
            return True

        exp = payload.get("exp")
        if not exp:
            return False
        return datetime.now(UTC).timestamp() < exp

    async def get_current_user_id(self, request: Request) -> UUID | None:
        """
        Get current authenticated user ID from request.

        Extracts user ID from the 'sub' claim in the JWT token.
        """
        if not self.enabled:
            return None

        token = self.extract_token(request)
        if not token:
            return None

        payload = await self.validate_token(token)
        if not payload:
            return None

        user_id_str = payload.get("sub")
        if not user_id_str:
            return None

        try:
            return UUID(user_id_str)
        except (ValueError, TypeError):
            return None

    async def get_current_client_id(self, request: Request) -> UUID | None:
        """
        Get current authenticated client ID from JWT token.

        Extracts client_id from the JWT token payload using the configured
        claim name (default: 'client_id'). Falls back to 'sub' if the
        configured claim is not found.

        Best Practice: client_id should be in the JWT token, not in URL path parameters,
        to prevent clients from accessing other clients' data by manipulating URLs.
        """
        token = self.extract_token(request)
        if not token:
            if not self.enabled:
                # Return a default client ID for development when auth is disabled
                return DEFAULT_CLIENT_ID
            return None

        payload = await self.validate_token(token)
        if not payload:
            if not self.enabled:
                # Return a default client ID for development when auth is disabled
                return DEFAULT_CLIENT_ID
            return None

        # Extract client_id from token payload using configured claim
        # Fall back to 'sub' if configured claim not found
        client_id_str = payload.get(self.client_id_claim)
        if not client_id_str:
            client_id_str = payload.get("sub")

        if not client_id_str:
            if not self.enabled:
                # Return a default client ID for development when auth is disabled
                return DEFAULT_CLIENT_ID
            return None

        try:
            return UUID(client_id_str)
        except (ValueError, TypeError):
            logger.warning(f"Invalid client_id format in JWT: {client_id_str}")
            if not self.enabled:
                # Return a default client ID for development when auth is disabled
                return DEFAULT_CLIENT_ID
            return None


# Global auth backend instance (initialized lazily)
_auth_backend: JWTAuthBackend | None = None


def get_auth_backend() -> JWTAuthBackend:
    """Get the global auth backend instance."""
    global _auth_backend
    if _auth_backend is None:
        from app.core.config import get_settings

        settings = get_settings()
        _auth_backend = JWTAuthBackend(
            secret_key=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            enabled=settings.auth_enabled,
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            client_id_claim=settings.jwt_client_id_claim,
        )
        if not settings.auth_enabled:
            logger.warning(
                "Authentication is DISABLED. All requests will use the default client ID. "
                "Set AUTH_ENABLED=true in production."
            )
        else:
            if settings.jwt_jwks_url:
                logger.info(f"JWT authentication enabled with JWKS from {settings.jwt_jwks_url}")
            else:
                logger.info(f"JWT authentication enabled with {settings.jwt_algorithm} algorithm")
    return _auth_backend


def reset_auth_backend() -> None:
    """Reset the global auth backend (for testing)."""
    global _auth_backend
    _auth_backend = None


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
            return DEFAULT_CLIENT_ID

    return client_id
