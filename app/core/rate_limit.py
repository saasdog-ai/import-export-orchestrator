"""Rate limiting middleware for API protection."""

import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any, cast

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimitConfig:
    """Configuration for rate limiting."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_limit: int = 10,
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit


# Default rate limits by endpoint type
DEFAULT_RATE_LIMITS = {
    "default": RateLimitConfig(requests_per_minute=60, requests_per_hour=1000),
    "export": RateLimitConfig(requests_per_minute=30, requests_per_hour=500),
    "import": RateLimitConfig(requests_per_minute=20, requests_per_hour=200),
    "upload": RateLimitConfig(requests_per_minute=10, requests_per_hour=100),
}


class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter using sliding window.

    Note: This is suitable for single-instance deployments.
    For multi-instance deployments, use Redis-based rate limiting.
    """

    def __init__(self):
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._cleanup_interval = 300  # Cleanup every 5 minutes
        self._last_cleanup = time.time()

    def _cleanup_old_entries(self, window_seconds: int = 3600) -> None:
        """Remove entries older than the window."""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        cutoff = current_time - window_seconds
        for key in list(self._requests.keys()):
            self._requests[key] = [t for t in self._requests[key] if t > cutoff]
            if not self._requests[key]:
                del self._requests[key]
        self._last_cleanup = current_time

    def is_allowed(self, key: str, config: RateLimitConfig) -> tuple[bool, dict[str, Any]]:
        """
        Check if request is allowed based on rate limits.

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        current_time = time.time()
        self._cleanup_old_entries()

        # Get request timestamps for this key
        timestamps = self._requests[key]

        # Count requests in different windows
        minute_ago = current_time - 60
        hour_ago = current_time - 3600

        requests_last_minute = sum(1 for t in timestamps if t > minute_ago)
        requests_last_hour = sum(1 for t in timestamps if t > hour_ago)

        # Check rate limits
        rate_limit_info = {
            "requests_last_minute": requests_last_minute,
            "requests_last_hour": requests_last_hour,
            "limit_per_minute": config.requests_per_minute,
            "limit_per_hour": config.requests_per_hour,
        }

        if requests_last_minute >= config.requests_per_minute:
            rate_limit_info["retry_after"] = int(60 - (current_time - timestamps[-1]))
            return False, rate_limit_info

        if requests_last_hour >= config.requests_per_hour:
            rate_limit_info["retry_after"] = int(3600 - (current_time - timestamps[0]))
            return False, rate_limit_info

        # Request allowed - record it
        self._requests[key].append(current_time)

        # Trim old entries to prevent memory growth
        self._requests[key] = [t for t in self._requests[key] if t > hour_ago]

        return True, rate_limit_info


# Global rate limiter instance
_rate_limiter = InMemoryRateLimiter()


def get_rate_limit_key(request: Request) -> str:
    """
    Generate a rate limit key based on client identifier.

    Uses client_id from request state if available, otherwise uses IP address.
    """
    # Try to get client_id from request state (set by auth middleware)
    client_id = getattr(request.state, "client_id", None)
    if client_id:
        return f"client:{client_id}"

    # Fall back to IP address
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"
    return f"ip:{ip}"


def get_endpoint_type(path: str) -> str:
    """Determine endpoint type for rate limiting."""
    if "/exports" in path:
        if "/upload" in path:
            return "upload"
        return "export"
    if "/imports" in path:
        if "/upload" in path:
            return "upload"
        return "import"
    return "default"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for API protection.

    Applies different rate limits based on:
    - Client identifier (client_id or IP address)
    - Endpoint type (export, import, upload, default)
    """

    def __init__(self, app: Any, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        if not self.enabled:
            return cast(Response, await call_next(request))

        # Skip rate limiting for health checks
        if request.url.path.startswith("/health"):
            return cast(Response, await call_next(request))

        # Get rate limit key and config
        key = get_rate_limit_key(request)
        endpoint_type = get_endpoint_type(request.url.path)
        config = DEFAULT_RATE_LIMITS.get(endpoint_type, DEFAULT_RATE_LIMITS["default"])

        # Check rate limit
        is_allowed, info = _rate_limiter.is_allowed(f"{key}:{endpoint_type}", config)

        if not is_allowed:
            retry_after = int(info.get("retry_after", 60))
            logger.warning(
                f"Rate limit exceeded for {key} on {endpoint_type}. "
                f"Requests: {info['requests_last_minute']}/min, {info['requests_last_hour']}/hour"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please slow down your requests.",
                headers={"Retry-After": str(retry_after)},
            )

        # Process request
        response: Response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(config.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            config.requests_per_minute - info["requests_last_minute"]
        )

        return response
