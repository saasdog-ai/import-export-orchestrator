"""Main FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api import exports, health, imports, jobs
from app.core.config import get_settings
from app.core.dependency_injection import (
    get_job_runner,
    get_scheduler_service,
    init_dependencies,
    shutdown_dependencies,
)
from app.core.logging import setup_logging

settings = get_settings()

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
    ],
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(jobs.router)
app.include_router(exports.router)
app.include_router(imports.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "status": "running",
    }
