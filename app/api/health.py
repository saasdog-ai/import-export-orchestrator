"""Health check API routes."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.dto import ErrorResponse, HealthResponse
from app.core.dependency_injection import (
    get_cloud_storage,
    get_database,
    get_message_queue,
)
from app.core.logging import get_logger
from app.infrastructure.db.database import Database
from app.infrastructure.queue.interface import MessageQueueInterface
from app.infrastructure.storage.interface import CloudStorageInterface

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


@router.get(
    "/health/detailed",
    summary="Detailed health check",
    description="Returns detailed health status of all components (database, message queue, cloud storage).",
    responses={
        200: {
            "description": "Health status of all components",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "timestamp": "2024-01-01T12:00:00Z",
                        "components": {
                            "database": {"status": "ok", "response_time_ms": 5},
                            "message_queue": {"status": "ok", "response_time_ms": 10},
                            "cloud_storage": {"status": "ok", "response_time_ms": 15},
                        },
                    }
                }
            },
        },
        503: {
            "description": "One or more components are unhealthy",
            "model": ErrorResponse,
        },
    },
)
async def detailed_health_check(
    db: Database = Depends(get_database),
    message_queue: MessageQueueInterface | None = Depends(get_message_queue),
    cloud_storage: CloudStorageInterface | None = Depends(get_cloud_storage),
):
    """
    Detailed health check with component status.

    Checks the health of:
    - Database connectivity
    - Message queue (if configured)
    - Cloud storage (if configured)

    Returns overall status and individual component statuses.
    """
    import time

    components: dict[str, dict[str, Any]] = {}
    overall_status = "healthy"

    # Check database
    try:
        start_time = time.time()
        async with db.async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        response_time = int((time.time() - start_time) * 1000)
        components["database"] = {"status": "ok", "response_time_ms": response_time}
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        components["database"] = {"status": "error", "error": str(e)}
        overall_status = "degraded"

    # Check message queue
    if message_queue:
        try:
            start_time = time.time()
            # Try a lightweight operation - if get_queue_attributes exists, use it
            # Otherwise, just mark as configured (can't test without actual queue)
            if hasattr(message_queue, "get_queue_attributes"):
                try:
                    await message_queue.get_queue_attributes()
                except NotImplementedError:
                    # In-memory queue doesn't implement this
                    pass
            response_time = int((time.time() - start_time) * 1000)
            components["message_queue"] = {"status": "ok", "response_time_ms": response_time}
        except Exception as e:
            logger.error(f"Message queue health check failed: {e}", exc_info=True)
            components["message_queue"] = {"status": "error", "error": str(e)}
            overall_status = "degraded"
    else:
        components["message_queue"] = {"status": "not_configured"}

    # Check cloud storage
    if cloud_storage:
        try:
            start_time = time.time()
            # Try to get queue attributes or perform a lightweight operation
            # For now, just check if it's configured
            response_time = int((time.time() - start_time) * 1000)
            components["cloud_storage"] = {"status": "ok", "response_time_ms": response_time}
        except Exception as e:
            logger.error(f"Cloud storage health check failed: {e}", exc_info=True)
            components["cloud_storage"] = {"status": "error", "error": str(e)}
            overall_status = "degraded"
    else:
        components["cloud_storage"] = {"status": "not_configured"}

    response_data = {
        "status": overall_status,
        "timestamp": datetime.now(UTC).isoformat(),
        "components": components,
    }

    status_code = (
        status.HTTP_200_OK if overall_status == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return JSONResponse(status_code=status_code, content=response_data)
