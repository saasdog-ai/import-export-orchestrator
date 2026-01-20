"""Data Transfer Objects (DTOs) for API requests and responses."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.entities import (
    ExportConfig,
    ExportEntity,
    ExportField,
    ExportFilterGroup,
    ImportConfig,
    ImportField,
    JobStatus,
    JobType,
)


class JobDefinitionCreate(BaseModel):
    """DTO for creating a job definition.

    The client_id must be provided and must match the authenticated client_id from JWT token.
    This provides defense in depth - the JWT token is the source of truth, but we validate
    that the request body matches to prevent mistakes or malicious attempts.
    """

    client_id: UUID
    name: str
    job_type: JobType
    export_config: ExportConfig | None = None
    import_config: ImportConfig | None = None
    cron_schedule: str | None = None
    enabled: bool = True


class JobDefinitionUpdate(BaseModel):
    """DTO for updating a job definition.

    Only 'safe' fields can be updated directly. Config fields (export_config,
    import_config) are immutable - use clone endpoint to create a new job
    with modified config.
    """

    name: str | None = None
    cron_schedule: str | None = None
    enabled: bool | None = None


class JobDefinitionClone(BaseModel):
    """DTO for cloning a job definition with optional modifications."""

    name: str  # Required - new job needs a name
    export_config: ExportConfig | None = None  # If provided, overrides source config
    import_config: ImportConfig | None = None  # If provided, overrides source config
    cron_schedule: str | None = None
    enabled: bool = True


class JobRunSummary(BaseModel):
    """Summary of a job run for embedding in job responses."""

    id: UUID
    status: JobStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


class JobDefinitionResponse(BaseModel):
    """DTO for job definition response."""

    id: UUID
    client_id: UUID
    name: str
    job_type: JobType
    export_config: ExportConfig | None = None
    import_config: ImportConfig | None = None
    cron_schedule: str | None = None
    enabled: bool
    created_at: datetime
    updated_at: datetime
    last_run: JobRunSummary | None = None


class JobRunResponse(BaseModel):
    """DTO for job run response."""

    id: UUID
    job_id: UUID
    status: JobStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    result_metadata: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class PaginatedJobsResponse(BaseModel):
    """Paginated response for job definitions."""

    items: list[JobDefinitionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ExportRequest(BaseModel):
    """Request to create and trigger an export job.

    The export will fetch data matching the specified filters and return it in CSV or JSON format.
    Field aliases allow renaming columns in the output file.
    """

    entity: ExportEntity = Field(..., description="Entity type to export")
    fields: list[ExportField] = Field(
        ...,
        description="Fields to include in the export. Use 'as' property to rename columns.",
        min_length=1,
    )
    filters: ExportFilterGroup | None = Field(
        default=None, description="Optional filters to limit exported records"
    )
    sort: list[dict[str, str]] | None = Field(
        default=None,
        description="Sort order. Each item needs 'field' and 'direction' (asc/desc)",
    )
    limit: int | None = Field(default=None, ge=1, le=10000, description="Max records to export")
    offset: int = Field(default=0, ge=0, description="Records to skip (pagination)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "entity": "bill",
                    "fields": [
                        {"field": "id"},
                        {"field": "amount", "as": "Total Amount"},
                        {"field": "vendor.name", "as": "Vendor"},
                    ],
                    "filters": {
                        "operator": "and",
                        "filters": [{"field": "status", "operator": "eq", "value": "paid"}],
                    },
                    "sort": [{"field": "date", "direction": "desc"}],
                    "limit": 100,
                }
            ]
        }
    }


class ExportPreviewRequest(BaseModel):
    """Request to preview export data before creating a job.

    Returns a sample of the data that would be exported, useful for verifying
    filters and field configurations before running a full export.
    """

    entity: ExportEntity = Field(..., description="Entity type to preview")
    fields: list[ExportField] = Field(
        ...,
        description="Fields to include. Use 'as' property to rename columns.",
        min_length=1,
    )
    filters: ExportFilterGroup | None = Field(
        default=None, description="Optional filters to limit records"
    )
    sort: list[dict[str, str]] | None = Field(
        default=None, description="Sort order for preview results"
    )
    limit: int = Field(default=20, ge=1, le=100, description="Max records to return in preview")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "entity": "bill",
                    "fields": [
                        {"field": "id"},
                        {"field": "amount", "as": "Total"},
                        {"field": "date"},
                    ],
                    "limit": 10,
                }
            ]
        }
    }


class ExportPreviewResponse(BaseModel):
    """DTO for export preview response."""

    entity: ExportEntity
    count: int
    records: list[dict[str, Any]]
    limit: int
    offset: int


class ExportResultResponse(BaseModel):
    """DTO for export result response."""

    run_id: UUID
    entity: ExportEntity
    status: JobStatus
    result_metadata: dict[str, Any] | None = None
    error_message: str | None = None


class ErrorResponse(BaseModel):
    """DTO for error response."""

    error: str
    detail: str | None = None


class HealthResponse(BaseModel):
    """DTO for health check response."""

    status: str
    timestamp: datetime


# ============================================================================
# Import Preview DTOs
# ============================================================================


class ImportPreviewRequest(BaseModel):
    """Request to preview import data with validation results.

    Returns all records from the uploaded file with validation status for each row.
    This allows users to see which records will succeed and which will fail before
    executing the import.
    """

    file_path: str = Field(
        ...,
        description="Path to the uploaded file (from /imports/upload response)",
    )
    entity: ExportEntity = Field(..., description="Entity type to import")
    field_mappings: list[ImportField] | None = Field(
        default=None,
        description="Optional field mappings from source columns to target fields. "
        "If not provided, source columns must match target field names exactly.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "file_path": "imports/client-123/temp/bills.csv",
                    "entity": "bill",
                    "field_mappings": [
                        {"source": "Total Amount", "target": "amount"},
                        {"source": "Invoice Date", "target": "date"},
                    ],
                }
            ]
        }
    }


class ImportPreviewRecordError(BaseModel):
    """Validation error for a specific field in an import record."""

    field: str = Field(..., description="Field name that has the error")
    message: str = Field(..., description="Error message describing the validation failure")


class ImportPreviewRecord(BaseModel):
    """A single record in the import preview with validation status."""

    row: int = Field(..., description="Row number in the source file (1-based)")
    data: dict[str, Any] = Field(..., description="Record data after field mapping applied")
    is_valid: bool = Field(..., description="Whether this record passes validation")
    errors: list[ImportPreviewRecordError] = Field(
        default_factory=list,
        description="Validation errors for this record (empty if valid)",
    )


class ImportPreviewResponse(BaseModel):
    """Response containing import preview with validation results."""

    file_path: str = Field(..., description="Path to the file being previewed")
    entity: ExportEntity = Field(..., description="Entity type being imported")
    total_records: int = Field(..., description="Total number of records in the file")
    valid_count: int = Field(..., description="Number of records that pass validation")
    invalid_count: int = Field(..., description="Number of records that fail validation")
    records: list[ImportPreviewRecord] = Field(
        ...,
        description="All records with validation status",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "file_path": "imports/client-123/temp/bills.csv",
                    "entity": "bill",
                    "total_records": 100,
                    "valid_count": 95,
                    "invalid_count": 5,
                    "records": [
                        {
                            "row": 1,
                            "data": {"amount": 1000, "date": "2024-01-15"},
                            "is_valid": True,
                            "errors": [],
                        },
                        {
                            "row": 2,
                            "data": {"amount": "invalid", "date": "2024-01-15"},
                            "is_valid": False,
                            "errors": [{"field": "amount", "message": "Must be a valid number"}],
                        },
                    ],
                }
            ]
        }
    }


class ImportExecuteRequest(BaseModel):
    """Request to execute an import from a validated file.

    This should be called after previewing the import to confirm the data looks correct.
    """

    file_path: str = Field(
        ...,
        description="Path to the uploaded file (from /imports/upload response)",
    )
    entity: ExportEntity = Field(..., description="Entity type to import")
    field_mappings: list[ImportField] | None = Field(
        default=None,
        description="Optional field mappings from source columns to target fields.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "file_path": "imports/client-123/temp/bills.csv",
                    "entity": "bill",
                    "field_mappings": [
                        {"source": "Total Amount", "target": "amount"},
                        {"source": "Invoice Date", "target": "date"},
                    ],
                }
            ]
        }
    }


# ============================================================================
# Schema DTOs
# ============================================================================


class SchemaFieldType(str, Enum):
    """Data types for schema fields."""

    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    UUID = "uuid"


class SchemaField(BaseModel):
    """Definition of a field in an entity schema."""

    name: str = Field(..., description="Field name (used in API requests)")
    type: str = Field(..., description="Data type (string, number, date, uuid, etc.)")
    label: str = Field(..., description="Human-readable label for display")
    required: bool = Field(default=False, description="Whether this field is required for imports")
    description: str | None = Field(default=None, description="Optional description of the field")


class SchemaRelationshipField(BaseModel):
    """A field available through a relationship."""

    name: str = Field(..., description="Field name on the related entity")
    type: str = Field(..., description="Data type")
    label: str = Field(..., description="Human-readable label")


class SchemaRelationship(BaseModel):
    """Definition of a relationship to another entity."""

    name: str = Field(..., description="Relationship name (used in field paths like 'vendor.name')")
    label: str = Field(..., description="Human-readable label")
    entity: str = Field(..., description="Name of the related entity")
    type: str = Field(
        default="many_to_one",
        description="Relationship type (many_to_one, one_to_many)",
    )
    fields: list[SchemaRelationshipField] = Field(
        ...,
        description="Fields available through this relationship",
    )


class SchemaEntity(BaseModel):
    """Definition of an entity in the schema."""

    name: str = Field(..., description="Entity name (used in API requests)")
    label: str = Field(..., description="Human-readable label for display")
    description: str | None = Field(default=None, description="Optional description")
    fields: list[SchemaField] = Field(..., description="Direct fields on this entity")
    relationships: list[SchemaRelationship] = Field(
        default_factory=list,
        description="Relationships to other entities",
    )


class SchemaResponse(BaseModel):
    """Response containing the full entity schema."""

    entities: list[SchemaEntity] = Field(..., description="All available entities")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "entities": [
                        {
                            "name": "bill",
                            "label": "Bills",
                            "fields": [
                                {"name": "id", "type": "uuid", "label": "ID"},
                                {"name": "amount", "type": "number", "label": "Amount"},
                                {"name": "date", "type": "date", "label": "Date"},
                            ],
                            "relationships": [
                                {
                                    "name": "vendor",
                                    "label": "Vendor",
                                    "entity": "vendor",
                                    "type": "many_to_one",
                                    "fields": [
                                        {"name": "name", "type": "string", "label": "Vendor Name"},
                                    ],
                                }
                            ],
                        }
                    ]
                }
            ]
        }
    }
