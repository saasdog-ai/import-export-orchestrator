"""SQLAlchemy database models."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.domain.entities import JobStatus
from app.infrastructure.db.database import Base


class JobDefinitionModel(Base):
    """Job definition database model."""

    __tablename__ = "job_definitions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    client_id = Column(
        PGUUID(as_uuid=True), nullable=False
    )  # No foreign key - clients managed in main SaaS app
    name = Column(String(255), nullable=False)
    job_type = Column(String(20), nullable=False)  # JobType enum as string
    export_config = Column(JSON, nullable=True)
    import_config = Column(JSON, nullable=True)
    cron_schedule = Column(String(100), nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    runs = relationship("JobRunModel", back_populates="job", cascade="all, delete-orphan")


class JobRunModel(Base):
    """Job run database model."""

    __tablename__ = "job_runs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id = Column(PGUUID(as_uuid=True), ForeignKey("job_definitions.id"), nullable=False)
    status = Column(String(20), default=JobStatus.PENDING.value, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    result_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    job = relationship("JobDefinitionModel", back_populates="runs")
