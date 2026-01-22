"""JWKS (JSON Web Key Set) fetcher with caching."""

import time
from typing import Any

import httpx
from jose import jwk
from jose.backends.base import Key

from app.core.logging import get_logger

logger = get_logger(__name__)


class JWKSFetchError(Exception):
    """Raised when JWKS fetch fails."""

    pass


class JWKSClient:
    """
    Client for fetching and caching JWKS (JSON Web Key Sets).

    Fetches public keys from a JWKS endpoint and caches them for efficient
    JWT validation. Supports automatic cache refresh based on TTL.
    """

    def __init__(self, jwks_url: str, cache_ttl: int = 3600):
        """
        Initialize JWKS client.

        Args:
            jwks_url: URL to fetch JWKS from (e.g., https://auth.example.com/.well-known/jwks.json)
            cache_ttl: Cache time-to-live in seconds (default: 1 hour)
        """
        self.jwks_url = jwks_url
        self.cache_ttl = cache_ttl
        self._keys: dict[str, Key] = {}
        self._jwks_data: dict[str, Any] = {}
        self._last_fetch: float = 0

    def _is_cache_valid(self) -> bool:
        """Check if the cached keys are still valid."""
        if not self._keys:
            return False
        return (time.time() - self._last_fetch) < self.cache_ttl

    async def _fetch_jwks(self) -> dict[str, Any]:
        """Fetch JWKS from the configured URL."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.jwks_url)
                response.raise_for_status()
                jwks_data = response.json()
                logger.info(f"Successfully fetched JWKS from {self.jwks_url}")
                return jwks_data
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching JWKS from {self.jwks_url}: {e}")
            raise JWKSFetchError(f"Failed to fetch JWKS: HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error(f"Request error fetching JWKS from {self.jwks_url}: {e}")
            raise JWKSFetchError(f"Failed to fetch JWKS: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error fetching JWKS from {self.jwks_url}: {e}")
            raise JWKSFetchError(f"Failed to fetch JWKS: {e}") from e

    def _parse_jwks(self, jwks_data: dict[str, Any]) -> dict[str, Key]:
        """Parse JWKS data into key objects indexed by key ID (kid)."""
        keys: dict[str, Key] = {}
        for key_data in jwks_data.get("keys", []):
            try:
                kid = key_data.get("kid")
                if not kid:
                    logger.warning("Skipping key without 'kid' in JWKS")
                    continue
                key = jwk.construct(key_data)
                keys[kid] = key
                logger.debug(f"Loaded key with kid={kid}, alg={key_data.get('alg')}")
            except Exception as e:
                logger.warning(f"Failed to parse key from JWKS: {e}")
                continue
        return keys

    async def get_keys(self, force_refresh: bool = False) -> dict[str, Key]:
        """
        Get cached keys, fetching from JWKS endpoint if needed.

        Args:
            force_refresh: Force a refresh of the cache even if not expired

        Returns:
            Dictionary mapping key IDs (kid) to key objects
        """
        if not force_refresh and self._is_cache_valid():
            return self._keys

        jwks_data = await self._fetch_jwks()
        self._jwks_data = jwks_data
        self._keys = self._parse_jwks(jwks_data)
        self._last_fetch = time.time()

        if not self._keys:
            logger.warning(f"No valid keys found in JWKS from {self.jwks_url}")

        return self._keys

    async def get_key(self, kid: str) -> Key | None:
        """
        Get a specific key by its key ID (kid).

        Args:
            kid: The key ID from the JWT header

        Returns:
            The key object, or None if not found
        """
        keys = await self.get_keys()
        key = keys.get(kid)

        if not key:
            # Key not found, try refreshing in case new keys were added
            logger.info(f"Key {kid} not found in cache, refreshing JWKS")
            keys = await self.get_keys(force_refresh=True)
            key = keys.get(kid)

        return key

    async def get_signing_key(self, token_headers: dict[str, Any]) -> Key | None:
        """
        Get the signing key for a JWT based on its headers.

        Args:
            token_headers: The JWT header dictionary (containing 'kid', 'alg', etc.)

        Returns:
            The key to use for verification, or None if not found
        """
        kid = token_headers.get("kid")
        if not kid:
            # If no kid in token, try to use the first key (single-key JWKS)
            keys = await self.get_keys()
            if len(keys) == 1:
                return next(iter(keys.values()))
            logger.warning("JWT has no 'kid' header and JWKS has multiple keys")
            return None

        return await self.get_key(kid)


# Global JWKS client instance (lazily initialized)
_jwks_client: JWKSClient | None = None


def get_jwks_client() -> JWKSClient | None:
    """Get the global JWKS client instance, or None if not configured."""
    global _jwks_client
    if _jwks_client is None:
        from app.core.config import get_settings

        settings = get_settings()
        if settings.jwt_jwks_url:
            _jwks_client = JWKSClient(
                jwks_url=settings.jwt_jwks_url,
                cache_ttl=settings.jwt_jwks_cache_ttl,
            )
            logger.info(f"Initialized JWKS client for {settings.jwt_jwks_url}")
    return _jwks_client


def reset_jwks_client() -> None:
    """Reset the global JWKS client (for testing)."""
    global _jwks_client
    _jwks_client = None
