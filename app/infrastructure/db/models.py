"""SQLAlchemy database models."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
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
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
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
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
    )

    job = relationship("JobDefinitionModel", back_populates="runs")


# Sample data tables for import/export operations
class SampleVendorModel(Base):
    """Sample vendor database model for import/export operations."""

    __tablename__ = "sample_vendors"
    __table_args__ = (
        UniqueConstraint("client_id", "external_id", name="uq_vendor_client_external_id"),
        Index("ix_vendor_external_id", "client_id", "external_id"),
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    client_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    external_id = Column(String(255), nullable=True)  # User's system identifier for upsert
    name = Column(String(255), nullable=False)
    email_address = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    tax_number = Column(String(50), nullable=True)
    is_supplier = Column(Boolean, default=True, nullable=False)
    is_customer = Column(Boolean, default=False, nullable=False)
    status = Column(String(20), default="ACTIVE", nullable=False)  # ACTIVE, ARCHIVED
    currency = Column(String(10), nullable=True)
    address = Column(JSON, nullable=True)  # Store address as JSON
    phone_numbers = Column(JSON, nullable=True)  # Store phone numbers as JSON array
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
    )


class SampleInvoiceModel(Base):
    """Sample invoice database model for import/export operations."""

    __tablename__ = "sample_invoices"
    __table_args__ = (
        UniqueConstraint("client_id", "external_id", name="uq_invoice_client_external_id"),
        Index("ix_invoice_external_id", "client_id", "external_id"),
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    client_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    external_id = Column(String(255), nullable=True)  # User's system identifier for upsert
    invoice_number = Column(String(100), nullable=True)
    contact_id = Column(PGUUID(as_uuid=True), ForeignKey("sample_vendors.id"), nullable=True)
    issue_date = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    paid_on_date = Column(DateTime, nullable=True)
    memo = Column(Text, nullable=True)
    currency = Column(String(10), nullable=True)
    exchange_rate = Column(Numeric(10, 4), nullable=True)
    sub_total = Column(Numeric(15, 2), nullable=True)
    total_tax_amount = Column(Numeric(15, 2), nullable=True)
    total_amount = Column(Numeric(15, 2), nullable=False)
    balance = Column(Numeric(15, 2), nullable=True)
    status = Column(String(20), nullable=True)  # DRAFT, SUBMITTED, PAID, etc.
    line_items = Column(JSON, nullable=True)  # Store line items as JSON array
    tracking_categories = Column(JSON, nullable=True)  # Store tracking categories as JSON
    contact = relationship("SampleVendorModel", foreign_keys=[contact_id], lazy="noload")
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
    )


class SampleBillModel(Base):
    """Sample bill database model for import/export operations."""

    __tablename__ = "sample_bills"
    __table_args__ = (
        UniqueConstraint("client_id", "external_id", name="uq_bill_client_external_id"),
        Index("ix_bill_external_id", "client_id", "external_id"),
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    client_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    external_id = Column(String(255), nullable=True)  # User's system identifier for upsert
    bill_number = Column(String(100), nullable=True)
    vendor_id = Column(PGUUID(as_uuid=True), ForeignKey("sample_vendors.id"), nullable=True)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("sample_projects.id"), nullable=True)
    amount = Column(Numeric(15, 2), nullable=False)
    date = Column(DateTime, nullable=False)
    due_date = Column(DateTime, nullable=True)
    paid_on_date = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)
    currency = Column(String(10), nullable=True)
    status = Column(String(20), nullable=True)  # pending, paid, overdue, etc.
    line_items = Column(JSON, nullable=True)  # Store line items as JSON array
    vendor = relationship("SampleVendorModel", foreign_keys=[vendor_id], lazy="noload")
    project = relationship("SampleProjectModel", foreign_keys=[project_id], lazy="noload")
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
    )


class SampleProjectModel(Base):
    """Sample project database model for import/export operations."""

    __tablename__ = "sample_projects"
    __table_args__ = (
        UniqueConstraint("client_id", "external_id", name="uq_project_client_external_id"),
        Index("ix_project_external_id", "client_id", "external_id"),
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    client_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    external_id = Column(String(255), nullable=True)  # User's system identifier for upsert
    code = Column(String(100), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=True)  # active, completed, cancelled, etc.
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    budget = Column(Numeric(15, 2), nullable=True)
    currency = Column(String(10), nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
    )
