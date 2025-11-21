"""Custom exception hierarchy for the application."""

from typing import Any


class ApplicationError(Exception):
    """Base exception for application errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    details: dict[str, Any] | None = None

    def __init__(
        self, message: str, error_code: str | None = None, details: dict[str, Any] | None = None
    ):
        """Initialize application error."""
        super().__init__(message)
        self.message = message
        if error_code:
            self.error_code = error_code
        if details:
            self.details = details

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for API response."""
        result: dict[str, Any] = {
            "error": {
                "code": self.error_code,
                "message": self.message,
            }
        }
        if self.details:
            result["error"]["details"] = self.details
        return result


class NotFoundError(ApplicationError):
    """Resource not found error."""

    status_code = 404
    error_code = "NOT_FOUND"

    def __init__(self, resource_type: str, resource_id: str | None = None):
        """Initialize not found error."""
        if resource_id:
            message = f"{resource_type} with ID {resource_id} not found"
        else:
            message = f"{resource_type} not found"
        super().__init__(message)


class ValidationError(ApplicationError):
    """Validation error with field-level details."""

    status_code = 400
    error_code = "VALIDATION_ERROR"

    def __init__(
        self,
        message: str,
        errors: list[dict[str, Any]] | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Initialize validation error."""
        super().__init__(message, details=details)
        self.errors = errors or []

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary with validation errors."""
        result = super().to_dict()
        if self.errors:
            result["error"]["validation_errors"] = self.errors
        return result


class UnauthorizedError(ApplicationError):
    """Unauthorized access error."""

    status_code = 401
    error_code = "UNAUTHORIZED"

    def __init__(self, message: str = "Authentication required"):
        """Initialize unauthorized error."""
        super().__init__(message)


class ForbiddenError(ApplicationError):
    """Forbidden access error."""

    status_code = 403
    error_code = "FORBIDDEN"

    def __init__(self, message: str = "Access denied"):
        """Initialize forbidden error."""
        super().__init__(message)


class ConflictError(ApplicationError):
    """Resource conflict error (e.g., duplicate resource)."""

    status_code = 409
    error_code = "CONFLICT"

    def __init__(self, message: str):
        """Initialize conflict error."""
        super().__init__(message)


class DatabaseError(ApplicationError):
    """Database operation error."""

    status_code = 500
    error_code = "DATABASE_ERROR"

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        """Initialize database error."""
        super().__init__(message, details=details)


class ExternalServiceError(ApplicationError):
    """External service error (SaaS API, cloud storage, etc.)."""

    status_code = 502
    error_code = "EXTERNAL_SERVICE_ERROR"

    def __init__(self, service_name: str, message: str, details: dict[str, Any] | None = None):
        """Initialize external service error."""
        full_message = f"{service_name} error: {message}"
        super().__init__(full_message, details=details)
        self.service_name = service_name
