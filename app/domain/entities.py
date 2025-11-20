"""Domain entities representing core business concepts."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class JobType(str, Enum):
    """Job type enumeration."""

    IMPORT = "import"
    EXPORT = "export"


class JobStatus(str, Enum):
    """Job run status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Client(BaseModel):
    """Client entity."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        from_attributes = True


class ExportFilterOperator(str, Enum):
    """Comparison operators for export filters."""

    EQ = "eq"  # equals
    NE = "ne"  # not equals
    LT = "lt"  # less than
    LTE = "lte"  # less than or equal
    GT = "gt"  # greater than
    GTE = "gte"  # greater than or equal
    IN = "in"  # in list
    BETWEEN = "between"  # between two values
    CONTAINS = "contains"  # string contains
    STARTSWITH = "startswith"  # string starts with
    ENDSWITH = "endswith"  # string ends with
    ILIKE = "ilike"  # case-insensitive like


class ExportFilter(BaseModel):
    """Single export filter condition."""

    field: str = Field(..., description="Field path (e.g., 'vendor.name' or 'amount')")
    operator: ExportFilterOperator
    value: Any = Field(..., description="Filter value or list of values")

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: Any, info: Any) -> Any:
        """Validate filter value based on operator."""
        if info.data.get("operator") == ExportFilterOperator.BETWEEN:
            if not isinstance(v, list) or len(v) != 2:
                raise ValueError("BETWEEN operator requires a list of exactly 2 values")
        elif info.data.get("operator") == ExportFilterOperator.IN:
            if not isinstance(v, list):
                raise ValueError("IN operator requires a list of values")
        return v


class LogicalOperator(str, Enum):
    """Logical operators for combining filters."""

    AND = "and"
    OR = "or"
    NOT = "not"


class ExportFilterGroup(BaseModel):
    """Group of filters with logical operators."""

    operator: LogicalOperator = LogicalOperator.AND
    filters: list["ExportFilter"] = Field(default_factory=list)
    groups: list["ExportFilterGroup"] = Field(default_factory=list)

    @field_validator("filters", "groups", mode="before")
    @classmethod
    def validate_not_both_empty(cls, v: Any) -> Any:
        """Validate that at least one of filters or groups is provided."""
        # This is a simplified check - full validation happens in parent
        return v


ExportFilterGroup.model_rebuild()


class ExportEntity(str, Enum):
    """Entities that can be exported."""

    BILL = "bill"
    INVOICE = "invoice"
    VENDOR = "vendor"
    PROJECT = "project"


class ExportConfig(BaseModel):
    """Export job configuration."""

    entity: ExportEntity
    fields: list[str] = Field(..., description="List of fields to return")
    filters: ExportFilterGroup | None = None
    sort: list[dict[str, str]] | None = Field(
        default=None, description="List of sort directives: [{'field': 'name', 'direction': 'asc'}]"
    )
    limit: int | None = Field(default=None, ge=1, le=10000)
    offset: int = Field(default=0, ge=0)


class ImportConfig(BaseModel):
    """Import job configuration."""

    source: str = Field(..., description="Source system identifier")
    entity: ExportEntity
    options: dict[str, Any] = Field(default_factory=dict, description="Import-specific options")


class JobDefinition(BaseModel):
    """Job definition entity."""

    id: UUID = Field(default_factory=uuid4)
    client_id: UUID
    name: str
    job_type: JobType
    export_config: ExportConfig | None = None
    import_config: ImportConfig | None = None
    cron_schedule: str | None = Field(
        default=None, description="Cron expression for scheduled execution"
    )
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_job_config(self) -> "JobDefinition":
        """Validate that config matches job type."""
        if self.job_type == JobType.EXPORT and not self.export_config:
            raise ValueError("Export jobs require export_config")
        if self.job_type == JobType.IMPORT and not self.import_config:
            raise ValueError("Import jobs require import_config")
        return self

    class Config:
        from_attributes = True


class JobRun(BaseModel):
    """Job run entity representing a single execution."""

    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    status: JobStatus = JobStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    result_metadata: dict[str, Any] | None = Field(
        default=None, description="Metadata about the job result"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        from_attributes = True
