"""Project entity handler for import/export operations."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import SampleProjectModel
from app.infrastructure.saas.utils import model_to_dict, parse_date

# Column map for SQL pushdown
_COLUMN_MAP: dict[str, Column] = {
    "id": SampleProjectModel.id,
    "external_id": SampleProjectModel.external_id,
    "code": SampleProjectModel.code,
    "name": SampleProjectModel.name,
    "description": SampleProjectModel.description,
    "status": SampleProjectModel.status,
    "start_date": SampleProjectModel.start_date,
    "end_date": SampleProjectModel.end_date,
    "budget": SampleProjectModel.budget,
    "currency": SampleProjectModel.currency,
    "created_at": SampleProjectModel.created_at,
    "updated_at": SampleProjectModel.updated_at,
}


class ProjectHandler:
    """Handler for project fetch, create, update, and delete operations."""

    def build_query(self, client_id: UUID) -> Select:
        """Return base SELECT filtered by client_id."""
        return select(SampleProjectModel).where(SampleProjectModel.client_id == client_id)

    def get_column(self, field_path: str) -> Column | None:
        """Resolve field path to SQLAlchemy column."""
        return _COLUMN_MAP.get(field_path)

    async def fetch(self, session: AsyncSession, client_id: UUID) -> list[dict[str, Any]]:
        """Fetch projects from database."""
        result = await session.execute(
            select(SampleProjectModel).where(SampleProjectModel.client_id == client_id)
        )
        projects = result.scalars().all()
        return [model_to_dict(p) for p in projects]

    async def find_existing(
        self,
        session: AsyncSession,
        client_id: UUID,
        match_key: str,
        match_value: Any,
    ) -> SampleProjectModel | None:
        """Find an existing project by match key."""
        if match_key == "external_id":
            result = await session.execute(
                select(SampleProjectModel).where(
                    SampleProjectModel.client_id == client_id,
                    SampleProjectModel.external_id == match_value,
                )
            )
            return result.scalar_one_or_none()
        elif match_key == "id":
            try:
                project_id = UUID(match_value)
                result = await session.execute(
                    select(SampleProjectModel).where(
                        SampleProjectModel.id == project_id,
                        SampleProjectModel.client_id == client_id,
                    )
                )
                return result.scalar_one_or_none()
            except ValueError:
                return None
        return None

    async def create(
        self,
        session: AsyncSession,
        record: dict[str, Any],
        client_id: UUID,
    ) -> dict[str, Any]:
        """Create a new project record."""
        project = SampleProjectModel(
            id=uuid4(),
            client_id=client_id,
            external_id=record.get("external_id"),
            code=record.get("code"),
            name=record.get("name", ""),
            description=record.get("description"),
            status=record.get("status", "active"),
            start_date=parse_date(record.get("start_date")),
            end_date=parse_date(record.get("end_date")),
            budget=record.get("budget"),
            currency=record.get("currency", "USD"),
        )
        session.add(project)
        return {"action": "created"}

    async def update(
        self,
        session: AsyncSession,
        existing: SampleProjectModel,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        """Update an existing project record."""
        date_fields = {"start_date", "end_date"}
        decimal_fields = {"budget"}
        skip_fields = {"id", "client_id"}

        for key, value in record.items():
            if key in skip_fields or not hasattr(existing, key):
                continue
            if value is None or value == "":
                continue
            if key in date_fields:
                setattr(existing, key, parse_date(value))
            elif key in decimal_fields:
                setattr(existing, key, Decimal(str(value)) if value else None)
            else:
                setattr(existing, key, value)

        existing.updated_at = datetime.now(UTC).replace(tzinfo=None)  # type: ignore[assignment]
        return {"action": "updated"}

    async def delete(
        self,
        session: AsyncSession,
        existing: SampleProjectModel,
    ) -> dict[str, Any]:
        """Delete a project record."""
        await session.delete(existing)
        return {"action": "deleted"}

    def get_required_fields(self) -> list[str]:
        """Return required fields for project import."""
        return ["code", "name"]
