"""Decorators for common functionality."""

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from fastapi import HTTPException, status
from sqlalchemy.exc import DisconnectionError, OperationalError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.constants import (
    MAX_RETRY_ATTEMPTS,
    RETRY_BACKOFF_MAX,
    RETRY_BACKOFF_MIN,
    RETRY_BACKOFF_MULTIPLIER,
)
from app.core.exceptions import ApplicationError, DatabaseError
from app.core.logging import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def retry_database_operation(func: F) -> F:
    """
    Decorator to retry database operations on transient failures.

    Retries on OperationalError and DisconnectionError with exponential backoff.
    """
    retry_decorator = retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(
            multiplier=RETRY_BACKOFF_MULTIPLIER, min=RETRY_BACKOFF_MIN, max=RETRY_BACKOFF_MAX
        ),
        retry=retry_if_exception_type((OperationalError, DisconnectionError)),
        reraise=True,
    )

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await retry_decorator(func)(*args, **kwargs)
        except (OperationalError, DisconnectionError) as e:
            logger.error(f"Database operation failed after retries: {e}", exc_info=True)
            raise DatabaseError(f"Database operation failed: {str(e)}") from e

    return wrapper  # type: ignore[return-value]


def handle_errors(func: F) -> F:
    """
    Decorator for consistent error handling in API endpoints.

    Converts application errors to appropriate HTTP exceptions.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except ApplicationError:
            # Let ApplicationError propagate - it will be handled by global exception handler
            raise
        except ValueError as e:
            # Convert ValueError to ValidationError
            from app.core.exceptions import ValidationError

            raise ValidationError(str(e)) from e
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            ) from e

    return wrapper  # type: ignore[return-value]
