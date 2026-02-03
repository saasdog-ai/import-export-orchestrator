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


class ImportMode(str, Enum):
    """Import mode for handling existing records."""

    CREATE = "create"  # Insert only - skip/fail if exists
    UPDATE = "update"  # Update only - skip if not exists
    UPSERT = "upsert"  # Create or update based on match key


class RecordAction(str, Enum):
    """Per-record action for import operations.

    Used when CSV has an _action column to specify action per row.
    Supports both full names and short codes (C, U, X, D).
    """

    CREATE = "create"
    UPDATE = "update"
    UPSERT = "upsert"
    DELETE = "delete"

    @classmethod
    def from_string(cls, value: str) -> "RecordAction | None":
        """Parse action from string, supporting short codes."""
        if not value:
            return None
        normalized = value.strip().upper()
        mapping = {
            "CREATE": cls.CREATE,
            "C": cls.CREATE,
            "INSERT": cls.CREATE,
            "I": cls.CREATE,
            "UPDATE": cls.UPDATE,
            "U": cls.UPDATE,
            "UPSERT": cls.UPSERT,
            "X": cls.UPSERT,
            "DELETE": cls.DELETE,
            "D": cls.DELETE,
        }
        return mapping.get(normalized)


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


class ExportField(BaseModel):
    """Export field definition with optional alias and formatting.

    Use this to specify which fields to export and optionally rename them in the output.
    The order of fields in the array determines the column order in CSV exports.
    """

    field: str = Field(
        ...,
        description="Source field path. Use dot notation for nested fields.",
        examples=["id", "amount", "vendor.name", "project.code"],
    )
    as_: str | None = Field(
        default=None,
        alias="as",
        description="Output column name/alias. If not specified, the source field name is used.",
        examples=["Bill ID", "Total Amount", "Vendor Name"],
    )
    format: str | None = Field(
        default=None,
        description="Format string for transformations (reserved for future use).",
        examples=["date:YYYY-MM-DD", "currency:USD"],
    )

    @property
    def output_name(self) -> str:
        """Get the output column/key name (alias if set, otherwise source field)."""
        return self.as_ if self.as_ is not None else self.field

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "examples": [
                {"field": "id"},
                {"field": "amount", "as": "Total Amount"},
                {"field": "vendor.name", "as": "Vendor Name"},
            ]
        },
    }


class ExportConfig(BaseModel):
    """Export job configuration.

    Defines what data to export, including entity type, fields, filters, and sorting.
    """

    entity: ExportEntity = Field(
        ...,
        description="The type of entity to export.",
    )
    fields: list[ExportField] = Field(
        ...,
        description="List of field definitions specifying which fields to export and their output names.",
        min_length=1,
    )

    @field_validator("fields", mode="before")
    @classmethod
    def convert_string_fields(cls, v: Any) -> list[dict[str, str]]:
        """Convert plain string fields to ExportField format for backward compatibility."""
        if not isinstance(v, list):
            return list(v) if v else []
        result: list[dict[str, str]] = []
        for item in v:
            if isinstance(item, str):
                # Convert old format "field_name" to new format {"field": "field_name"}
                result.append({"field": item})
            else:
                result.append(item)
        return result

    filters: ExportFilterGroup | None = Field(
        default=None,
        description="Optional filter criteria to limit exported records.",
    )
    sort: list[dict[str, str]] | None = Field(
        default=None,
        description="Sort order for exported records. Each item should have 'field' and 'direction' (asc/desc).",
        examples=[
            [{"field": "date", "direction": "desc"}, {"field": "amount", "direction": "asc"}]
        ],
    )
    limit: int | None = Field(
        default=None,
        ge=1,
        le=100000,
        description="Maximum number of records to export.",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of records to skip (for pagination).",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "entity": "bill",
                    "fields": [
                        {"field": "id"},
                        {"field": "amount", "as": "Total Amount"},
                        {"field": "date", "as": "Bill Date"},
                        {"field": "vendor.name", "as": "Vendor Name"},
                    ],
                    "filters": {
                        "operator": "and",
                        "filters": [{"field": "amount", "operator": "gt", "value": 1000}],
                    },
                    "sort": [{"field": "date", "direction": "desc"}],
                    "limit": 100,
                }
            ]
        }
    }

    def get_source_fields(self) -> list[str]:
        """Get list of source field names for querying."""
        return [f.field for f in self.fields]

    def get_field_mappings(self) -> dict[str, str]:
        """Get mapping from source field to output name."""
        return {f.field: f.output_name for f in self.fields}


class ImportField(BaseModel):
    """Import field mapping definition.

    Use this to map source column names (from CSV/JSON files) to target database fields.
    This allows importing files with different column naming conventions.
    """

    source: str = Field(
        ...,
        description="Source column name in the import file.",
        examples=["Total Amount", "Invoice Date", "Supplier Name"],
    )
    target: str = Field(
        ...,
        description="Target database field name.",
        examples=["amount", "date", "vendor_name"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"source": "Total Amount", "target": "amount"},
                {"source": "Invoice Date", "target": "date"},
                {"source": "Supplier Name", "target": "vendor_name"},
            ]
        }
    }


class ImportConfig(BaseModel):
    """Import job configuration.

    Defines how to import data, including entity type, field mappings, and options.
    """

    source: str = Field(..., description="Source system identifier")
    entity: ExportEntity = Field(..., description="The type of entity to import")
    fields: list[ImportField] | None = Field(
        default=None,
        description="Optional field mappings from source columns to target fields. "
        "If not provided, source columns must match target field names exactly.",
    )
    import_mode: ImportMode = Field(
        default=ImportMode.CREATE,
        description="How to handle existing records: create (insert only), "
        "update (update only), or upsert (create or update).",
    )
    match_key: str = Field(
        default="external_id",
        description="Field to match existing records for update/upsert modes. "
        "Typically 'external_id' which should be unique per client.",
    )
    options: dict[str, Any] = Field(default_factory=dict, description="Import-specific options")

    def get_field_mappings(self) -> dict[str, str]:
        """Get mapping from source column to target field.

        Returns:
            Dictionary mapping source column names to target field names.
            Empty dict if no mappings are configured.
        """
        if not self.fields:
            return {}
        return {f.source: f.target for f in self.fields}

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "source": "cloud_storage",
                    "entity": "bill",
                    "import_mode": "upsert",
                    "match_key": "external_id",
                    "fields": [
                        {"source": "Total Amount", "target": "amount"},
                        {"source": "Invoice Date", "target": "date"},
                    ],
                    "options": {"source_file": "imports/client-123/temp/bills.csv"},
                }
            ]
        }
    }


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
