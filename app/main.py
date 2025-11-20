"""Main FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    description="Backend job runner service for async import/export operations with scheduling and filtering",
    version="0.1.0",
    lifespan=lifespan,
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
