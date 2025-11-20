"""Data Transfer Objects (DTOs) for API requests and responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.entities import (
    ExportConfig,
    ExportEntity,
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
    """DTO for export job request."""

    entity: ExportEntity
    fields: list[str] = Field(..., description="List of fields to return")
    filters: ExportFilterGroup | None = None
    sort: list[dict[str, str]] | None = None
    limit: int | None = Field(default=None, ge=1, le=10000)
    offset: int = Field(default=0, ge=0)


class ExportPreviewRequest(BaseModel):
    """DTO for export preview request."""

    entity: ExportEntity
    fields: list[str] = Field(..., description="List of fields to return")
    filters: ExportFilterGroup | None = None
    sort: list[dict[str, str]] | None = None
    limit: int = Field(default=20, ge=1, le=100)


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
