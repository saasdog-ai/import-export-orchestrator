"""Vendor entity handler for import/export operations."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import SampleVendorModel
from app.infrastructure.saas.utils import model_to_dict

# Column map for SQL pushdown
_COLUMN_MAP: dict[str, Column] = {
    "id": SampleVendorModel.id,
    "external_id": SampleVendorModel.external_id,
    "name": SampleVendorModel.name,
    "email_address": SampleVendorModel.email_address,
    "email": SampleVendorModel.email_address,
    "phone": SampleVendorModel.phone,
    "tax_number": SampleVendorModel.tax_number,
    "is_supplier": SampleVendorModel.is_supplier,
    "is_customer": SampleVendorModel.is_customer,
    "status": SampleVendorModel.status,
    "currency": SampleVendorModel.currency,
    "created_at": SampleVendorModel.created_at,
    "updated_at": SampleVendorModel.updated_at,
}


class VendorHandler:
    """Handler for vendor fetch, create, update, and delete operations."""

    def build_query(self, client_id: UUID) -> Select:
        """Return base SELECT filtered by client_id."""
        return select(SampleVendorModel).where(SampleVendorModel.client_id == client_id)

    def get_column(self, field_path: str) -> Column | None:
        """Resolve field path to SQLAlchemy column."""
        return _COLUMN_MAP.get(field_path)

    async def fetch(self, session: AsyncSession, client_id: UUID) -> list[dict[str, Any]]:
        """Fetch vendors from database."""
        result = await session.execute(
            select(SampleVendorModel).where(SampleVendorModel.client_id == client_id)
        )
        vendors = result.scalars().all()
        return [model_to_dict(v) for v in vendors]

    async def find_existing(
        self,
        session: AsyncSession,
        client_id: UUID,
        match_key: str,
        match_value: Any,
    ) -> SampleVendorModel | None:
        """Find an existing vendor by match key."""
        if match_key == "external_id":
            result = await session.execute(
                select(SampleVendorModel).where(
                    SampleVendorModel.client_id == client_id,
                    SampleVendorModel.external_id == match_value,
                )
            )
            return result.scalar_one_or_none()
        elif match_key == "id":
            try:
                vendor_id = UUID(match_value)
                result = await session.execute(
                    select(SampleVendorModel).where(
                        SampleVendorModel.id == vendor_id,
                        SampleVendorModel.client_id == client_id,
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
        """Create a new vendor record."""
        vendor = SampleVendorModel(
            id=uuid4(),
            client_id=client_id,
            external_id=record.get("external_id"),
            name=record.get("name", ""),
            email_address=record.get("email_address") or record.get("email"),
            phone=record.get("phone"),
            tax_number=record.get("tax_number"),
            is_supplier=record.get("is_supplier", True),
            is_customer=record.get("is_customer", False),
            status=record.get("status", "ACTIVE"),
            currency=record.get("currency", "USD"),
            address=record.get("address"),
            phone_numbers=record.get("phone_numbers"),
        )
        session.add(vendor)
        return {"action": "created"}

    async def update(
        self,
        session: AsyncSession,
        existing: SampleVendorModel,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        """Update an existing vendor record."""
        for key, value in record.items():
            if key not in ["id", "client_id"] and hasattr(existing, key):
                setattr(existing, key, value)
        existing.updated_at = datetime.now(UTC).replace(tzinfo=None)  # type: ignore[assignment]
        return {"action": "updated"}

    async def delete(
        self,
        session: AsyncSession,
        existing: SampleVendorModel,
    ) -> dict[str, Any]:
        """Delete a vendor record."""
        await session.delete(existing)
        return {"action": "deleted"}

    def get_required_fields(self) -> list[str]:
        """Return required fields for vendor import."""
        return ["name"]
