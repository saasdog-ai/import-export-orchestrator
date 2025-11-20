"""Database connection and session management."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


class Database:
    """Database connection manager."""

    def __init__(self, database_url: str, pool_size: int = 10, max_overflow: int = 20):
        """Initialize database connection."""
        self.database_url = database_url
        self.engine = create_async_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
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

