"""Data Transfer Objects (DTOs) for API requests and responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional
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
    """DTO for creating a job definition."""

    client_id: UUID
    name: str
    job_type: JobType
    export_config: Optional[ExportConfig] = None
    import_config: Optional[ImportConfig] = None
    cron_schedule: Optional[str] = None
    enabled: bool = True


class JobDefinitionUpdate(BaseModel):
    """DTO for updating a job definition."""

    name: Optional[str] = None
    export_config: Optional[ExportConfig] = None
    import_config: Optional[ImportConfig] = None
    cron_schedule: Optional[str] = None
    enabled: Optional[bool] = None


class JobDefinitionResponse(BaseModel):
    """DTO for job definition response."""

    id: UUID
    client_id: UUID
    name: str
    job_type: JobType
    export_config: Optional[ExportConfig] = None
    import_config: Optional[ImportConfig] = None
    cron_schedule: Optional[str] = None
    enabled: bool
    created_at: datetime
    updated_at: datetime


class JobRunResponse(BaseModel):
    """DTO for job run response."""

    id: UUID
    job_id: UUID
    status: JobStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class ExportRequest(BaseModel):
    """DTO for export job request."""

    entity: ExportEntity
    fields: List[str] = Field(..., description="List of fields to return")
    filters: Optional[ExportFilterGroup] = None
    sort: Optional[List[Dict[str, str]]] = None
    limit: Optional[int] = Field(default=None, ge=1, le=10000)
    offset: int = Field(default=0, ge=0)


class ExportPreviewRequest(BaseModel):
    """DTO for export preview request."""

    entity: ExportEntity
    fields: List[str] = Field(..., description="List of fields to return")
    filters: Optional[ExportFilterGroup] = None
    sort: Optional[List[Dict[str, str]]] = None
    limit: int = Field(default=20, ge=1, le=100)


class ExportPreviewResponse(BaseModel):
    """DTO for export preview response."""

    entity: ExportEntity
    count: int
    records: List[Dict[str, Any]]
    limit: int
    offset: int


class ExportResultResponse(BaseModel):
    """DTO for export result response."""

    run_id: UUID
    entity: ExportEntity
    status: JobStatus
    result_metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class ErrorResponse(BaseModel):
    """DTO for error response."""

    error: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    """DTO for health check response."""

    status: str
    timestamp: datetime

