"""Health check API routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text

from app.api.dto import ErrorResponse, HealthResponse
from app.core.dependency_injection import get_database
from app.infrastructure.db.database import Database

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint."""
    return HealthResponse(status="healthy", timestamp=datetime.utcnow())


@router.get(
    "/health/db",
    response_model=HealthResponse,
    responses={503: {"model": ErrorResponse}},
)
async def health_check_db(db: Database = Depends(get_database)):
    """Database connectivity health check."""
    try:
        async with db.async_session_maker() as session:
            # Test database connection
            result = await session.execute(text("SELECT 1"))
            result.scalar()
        return HealthResponse(status="healthy", timestamp=datetime.utcnow())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}",
        )

