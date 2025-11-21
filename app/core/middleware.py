"""Middleware for request/response processing."""

import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation ID to requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add correlation ID."""
        # Get or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

        # Add to request state for use in handlers
        request.state.correlation_id = correlation_id

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        return response
