"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.domain.entities import (
    ExportConfig,
    ExportEntity,
    ImportConfig,
    JobDefinition,
    JobType,
)
from app.infrastructure.db.database import Base, Database
from app.infrastructure.db.repositories import JobRepository, JobRunRepository
from app.infrastructure.query.engine import ExportQueryEngine
from app.infrastructure.saas.client import MockSaaSApiClient
from app.infrastructure.scheduling.scheduler import APSchedulerService
from app.main import app
from app.services.job_runner import JobRunnerService
from app.services.job_service import JobService
from app.services.scheduler_service import SchedulerService

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_job_runner"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db():
    """Create test database."""
    # Create engine with NullPool for tests - use asyncpg driver
    engine = create_async_engine(
        TEST_DATABASE_URL,  # Keep +asyncpg for async driver
        poolclass=NullPool,
        echo=False,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create database wrapper
    db = Database(TEST_DATABASE_URL)
    await db.connect()

    yield db

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await db.disconnect()
    await engine.dispose()


@pytest.fixture
async def db_session(test_db: Database) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async with test_db.async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture
def test_client_id():
    """Create a test client ID."""
    return uuid4()


@pytest.fixture
def test_job(test_client_id) -> JobDefinition:
    """Create a test job definition."""
    export_config = ExportConfig(
        entity=ExportEntity.BILL,
        fields=["id", "amount", "date"],
        limit=100,
    )
    return JobDefinition(
        id=uuid4(),
        client_id=test_client_id,
        name="Test Job",
        job_type=JobType.EXPORT,
        export_config=export_config,
        enabled=True,
    )


@pytest.fixture
def test_import_job(test_client_id) -> JobDefinition:
    """Create a test import job definition."""
    import_config = ImportConfig(
        source="test_source",
        entity=ExportEntity.BILL,
        options={},
    )
    return JobDefinition(
        id=uuid4(),
        client_id=test_client_id,
        name="Test Import Job",
        job_type=JobType.IMPORT,
        import_config=import_config,
        enabled=True,
    )


@pytest.fixture
async def job_repository(test_db: Database) -> JobRepository:
    """Create a job repository."""
    return JobRepository(test_db)


@pytest.fixture
async def job_run_repository(test_db: Database) -> JobRunRepository:
    """Create a job run repository."""
    return JobRunRepository(test_db)


@pytest.fixture
async def query_engine(test_db: Database, saas_client: MockSaaSApiClient) -> ExportQueryEngine:
    """Create a query engine."""
    return ExportQueryEngine(test_db, saas_client)


@pytest.fixture
async def saas_client() -> MockSaaSApiClient:
    """Create a mock SaaS client."""
    return MockSaaSApiClient()


@pytest.fixture
def scheduler() -> APSchedulerService:
    """Create a scheduler."""
    return APSchedulerService(timezone="UTC")


@pytest.fixture
async def job_runner(
    test_db: Database,
    job_repository: JobRepository,
    job_run_repository: JobRunRepository,
    query_engine: ExportQueryEngine,
    saas_client: MockSaaSApiClient,
) -> JobRunnerService:
    """Create a job runner service."""
    runner = JobRunnerService(
        job_repository=job_repository,
        job_run_repository=job_run_repository,
        query_engine=query_engine,
        saas_client=saas_client,
        max_workers=2,
    )
    await runner.start()
    yield runner
    await runner.stop()


@pytest.fixture
async def scheduler_service(
    scheduler: APSchedulerService,
    test_db: Database,
    job_runner: JobRunnerService,
) -> SchedulerService:
    """Create a scheduler service."""
    job_repository = JobRepository(test_db)
    job_run_repository = JobRunRepository(test_db)
    return SchedulerService(
        scheduler=scheduler,
        job_repository=job_repository,
        job_run_repository=job_run_repository,
        job_runner=job_runner,
    )


@pytest.fixture
async def job_service(
    test_db: Database,
    scheduler_service: SchedulerService,
    job_runner: JobRunnerService,
) -> JobService:
    """Create a job service."""
    job_repository = JobRepository(test_db)
    job_run_repository = JobRunRepository(test_db)
    return JobService(
        job_repository=job_repository,
        job_run_repository=job_run_repository,
        scheduler_service=scheduler_service,
        job_runner=job_runner,
    )


@pytest.fixture
async def test_client_app():
    """Create a test client for FastAPI."""
    from httpx import AsyncClient
    from httpx._transports.asgi import ASGITransport

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
