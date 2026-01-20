"""Main FastAPI application entry point."""

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import exports, health, imports, jobs, schema
from app.core.config import get_settings
from app.core.dependency_injection import (
    get_job_runner,
    get_scheduler_service,
    init_dependencies,
    shutdown_dependencies,
)
from app.core.exceptions import ApplicationError
from app.core.logging import get_logger, setup_logging
from app.core.middleware import CorrelationIDMiddleware, SecurityHeadersMiddleware
from app.core.rate_limit import RateLimitMiddleware

settings = get_settings()
logger = get_logger(__name__)

# Setup logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await init_dependencies()

    # Start job runner
    job_runner = get_job_runner()
    await job_runner.start()

    # Reload scheduled jobs
    scheduler_service = get_scheduler_service()
    await scheduler_service.reload_all_scheduled_jobs()

    yield

    # Shutdown
    await job_runner.stop()
    await shutdown_dependencies()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="""
    ## Import/Export Orchestrator API

    A comprehensive backend service for managing asynchronous import and export operations
    with advanced scheduling, filtering, and cloud storage integration.

    ### Features

    - **Job Management**: Create, update, and manage import/export job definitions
    - **Scheduled Jobs**: Support for cron-based job scheduling
    - **Date Filtering**: Filter jobs and runs by date ranges
    - **Cloud Storage**: Integration with AWS S3, Azure Blob Storage, and GCP Cloud Storage
    - **Multi-Phase Imports**: Upload, validate, and execute import operations
    - **Export Operations**: Query and export data with advanced filtering and sorting

    ### Authentication

    The API uses JWT token-based authentication. Include the token in the Authorization header:
    ```
    Authorization: Bearer <your-token>
    ```

    ### API Documentation

    - **Swagger UI**: `/docs` - Interactive API documentation
    - **ReDoc**: `/redoc` - Alternative API documentation
    - **OpenAPI JSON**: `/openapi.json` - OpenAPI 3.1 specification
    """,
    version="0.1.0",
    lifespan=lifespan,
    terms_of_service="https://example.com/terms/",
    contact={
        "name": "API Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "health",
            "description": "Health check endpoints for monitoring service availability and database connectivity.",
        },
        {
            "name": "jobs",
            "description": "Job management operations. Create, update, and manage import/export job definitions with scheduling support.",
        },
        {
            "name": "exports",
            "description": "Export operations. Create export jobs, preview data, and download exported files.",
        },
        {
            "name": "imports",
            "description": "Import operations. Upload files, validate data, and execute import jobs.",
        },
        {
            "name": "schema",
            "description": "Schema discovery. Get metadata about available entities, fields, and relationships.",
        },
    ],
)

# Add correlation ID middleware
app.add_middleware(CorrelationIDMiddleware)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware, enabled=settings.rate_limit_enabled)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
    expose_headers=["X-Correlation-ID"],
    max_age=3600,
)

# Include routers
app.include_router(health.router)
app.include_router(jobs.router)
app.include_router(exports.router)
app.include_router(imports.router)
app.include_router(schema.router)


def custom_openapi():
    """Generate custom OpenAPI schema with OpenAPI 3.1 support."""
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        openapi_version="3.1.0",  # Use OpenAPI 3.1.0
    )
    # Add additional metadata for OpenAPI 3.1
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Global exception handlers
@app.exception_handler(ApplicationError)
async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
    """Handle application-specific errors."""
    correlation_id = getattr(request.state, "correlation_id", str(uuid4()))
    logger.error(
        f"Application error: {exc.error_code} - {exc.message}",
        extra={
            "correlation_id": correlation_id,
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
        },
    )
    error_response = exc.to_dict()
    error_response["error"]["correlation_id"] = correlation_id
    return JSONResponse(status_code=exc.status_code, content=error_response)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    correlation_id = getattr(request.state, "correlation_id", str(uuid4()))
    logger.error(
        f"Unhandled exception: {exc}",
        exc_info=True,
        extra={
            "correlation_id": correlation_id,
            "path": request.url.path,
            "method": request.method,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
                "correlation_id": correlation_id,
            }
        },
    )


@app.get(
    "/",
    summary="Root endpoint",
    description="Returns basic information about the API service.",
    tags=["health"],
    response_description="Service information including name, version, and status.",
)
async def root():
    """
    Root endpoint providing service information.

    Returns basic metadata about the API service including:
    - Service name
    - API version
    - Current status
    - Documentation URLs
    """
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "status": "running",
        "docs": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json",
        },
    }
