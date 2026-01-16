"""Data Transfer Objects (DTOs) for API requests and responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.entities import (
    ExportConfig,
    ExportEntity,
    ExportField,
    ExportFilterGroup,
    ImportConfig,
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
    """DTO for updating a job definition."""

    name: str | None = None
    export_config: ExportConfig | None = None
    import_config: ImportConfig | None = None
    cron_schedule: str | None = None
    enabled: bool | None = None


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
