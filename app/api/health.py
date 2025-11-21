"""Health check API routes."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text

from app.api.dto import ErrorResponse, HealthResponse
from app.core.dependency_injection import get_database
from app.core.logging import get_logger
from app.infrastructure.db.database import Database

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Basic health check",
    description="Returns the health status of the API service.",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "timestamp": "2024-01-01T12:00:00Z",
                    }
                }
            },
        },
    },
)
async def health_check():
    """
    Basic health check endpoint.

    Returns the current health status of the API service.
    This endpoint does not check database connectivity.
    """
    # Log health check request
    logger.debug("Health check request received")
    response = HealthResponse(status="healthy", timestamp=datetime.now(UTC))
    logger.debug(f"Health check response: status={response.status}")
    return response


@router.get(
    "/health/db",
    response_model=HealthResponse,
    summary="Database health check",
    description="Checks the connectivity and health of the database connection.",
    responses={
        200: {
            "description": "Database is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "timestamp": "2024-01-01T12:00:00Z",
                    }
                }
            },
        },
        503: {
            "description": "Database connection failed",
            "model": ErrorResponse,
        },
    },
)
async def health_check_db(db: Database = Depends(get_database)):
    """
    Database connectivity health check.

    Performs a test query to verify database connectivity.
    Returns 503 if the database is unreachable.
    """
    try:
        async with db.async_session_maker() as session:
            # Test database connection
            result = await session.execute(text("SELECT 1"))
            result.scalar()
        return HealthResponse(status="healthy", timestamp=datetime.now(UTC))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}",
        ) from e
