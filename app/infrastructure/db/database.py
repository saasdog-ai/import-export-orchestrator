"""Database connection and session management."""

from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.constants import (
    DEFAULT_MAX_OVERFLOW,
    DEFAULT_POOL_RECYCLE,
    DEFAULT_POOL_SIZE,
    DEFAULT_POOL_TIMEOUT,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


class Database:
    """Database connection manager with transaction support."""

    def __init__(
        self,
        database_url: str,
        pool_size: int = DEFAULT_POOL_SIZE,
        max_overflow: int = DEFAULT_MAX_OVERFLOW,
        pool_recycle: int = DEFAULT_POOL_RECYCLE,
        pool_timeout: int = DEFAULT_POOL_TIMEOUT,
    ):
        """Initialize database connection with improved pool configuration."""
        self.database_url = database_url
        self.engine = create_async_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=pool_recycle,  # Recycle connections after this many seconds
            pool_timeout=pool_timeout,  # Timeout for getting connection from pool
            echo=False,
        )
        self.async_session_maker = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def connect(self) -> None:
        """Connect to database."""
        # Test connection
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: sync_conn.execute(text("SELECT 1")))
        logger.info("Database connection established")

    async def disconnect(self) -> None:
        """Disconnect from database."""
        await self.engine.dispose()
        logger.info("Database connection closed")

    def get_session(self) -> AsyncSession:
        """Get async database session."""
        return self.async_session_maker()

    @asynccontextmanager
    async def transaction(self):
        """
        Context manager for database transactions.

        Automatically commits on success and rolls back on error.

        Example:
            async with db.transaction() as session:
                # Perform operations
                session.add(model)
                # Auto-commits on success, auto-rollbacks on error
        """
        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
