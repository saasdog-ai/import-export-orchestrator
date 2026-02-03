"""Bill entity handler for import/export operations."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.db.models import (
    SampleBillModel,
    SampleProjectModel,
    SampleVendorModel,
)
from app.infrastructure.saas.utils import model_to_dict, parse_date

# Column map for SQL pushdown (includes relationship fields via dot notation)
_COLUMN_MAP: dict[str, Column] = {
    "id": SampleBillModel.id,
    "external_id": SampleBillModel.external_id,
    "bill_number": SampleBillModel.bill_number,
    "vendor_id": SampleBillModel.vendor_id,
    "project_id": SampleBillModel.project_id,
    "amount": SampleBillModel.amount,
    "date": SampleBillModel.date,
    "due_date": SampleBillModel.due_date,
    "paid_on_date": SampleBillModel.paid_on_date,
    "description": SampleBillModel.description,
    "currency": SampleBillModel.currency,
    "status": SampleBillModel.status,
    "created_at": SampleBillModel.created_at,
    "updated_at": SampleBillModel.updated_at,
    # Relationship columns
    "vendor.name": SampleVendorModel.name,
    "vendor.email_address": SampleVendorModel.email_address,
    "vendor.email": SampleVendorModel.email_address,
    "vendor.id": SampleVendorModel.id,
    "vendor.status": SampleVendorModel.status,
    "project.code": SampleProjectModel.code,
    "project.name": SampleProjectModel.name,
    "project.id": SampleProjectModel.id,
    "project.status": SampleProjectModel.status,
    "project.budget": SampleProjectModel.budget,
}


class BillHandler:
    """Handler for bill fetch, create, update, and delete operations."""

    def build_query(self, client_id: UUID) -> Select:
        """Return base SELECT with eager-loaded relationships, filtered by client_id."""
        return (
            select(SampleBillModel)
            .where(SampleBillModel.client_id == client_id)
            .options(
                selectinload(SampleBillModel.vendor),
                selectinload(SampleBillModel.project),
            )
        )

    def get_column(self, field_path: str) -> Column | None:
        """Resolve field path to SQLAlchemy column."""
        return _COLUMN_MAP.get(field_path)

    async def fetch(self, session: AsyncSession, client_id: UUID) -> list[dict[str, Any]]:
        """Fetch bills from database with nested vendor and project data."""
        result = await session.execute(
            select(SampleBillModel)
            .where(SampleBillModel.client_id == client_id)
            .order_by(SampleBillModel.date.desc())
            .options(
                selectinload(SampleBillModel.vendor),
                selectinload(SampleBillModel.project),
            )
        )
        bills = result.scalars().all()

        bills_dict = []
        for bill in bills:
            bill_dict = model_to_dict(bill)

            if bill.vendor:
                bill_dict["vendor"] = model_to_dict(bill.vendor)
                bill_dict["vendor_id"] = str(bill.vendor_id)

            if bill.project:
                bill_dict["project"] = model_to_dict(bill.project)
                bill_dict["project_id"] = str(bill.project_id)

            bills_dict.append(bill_dict)

        return bills_dict

    async def find_existing(
        self,
        session: AsyncSession,
        client_id: UUID,
        match_key: str,
        match_value: Any,
    ) -> SampleBillModel | None:
        """Find an existing bill by match key."""
        if match_key == "external_id":
            result = await session.execute(
                select(SampleBillModel).where(
                    SampleBillModel.client_id == client_id,
                    SampleBillModel.external_id == match_value,
                )
            )
            return result.scalar_one_or_none()
        elif match_key == "id":
            try:
                bill_id = UUID(match_value)
                result = await session.execute(
                    select(SampleBillModel).where(
                        SampleBillModel.id == bill_id,
                        SampleBillModel.client_id == client_id,
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
        """Create a new bill record."""
        vendor_id = None
        if record.get("vendor_id"):
            vendor_id = UUID(record["vendor_id"])
        elif record.get("vendor") and record["vendor"].get("id"):
            vendor_id = UUID(record["vendor"]["id"])

        project_id = None
        if record.get("project_id"):
            project_id = UUID(record["project_id"])
        elif record.get("project") and record["project"].get("id"):
            project_id = UUID(record["project"]["id"])

        bill = SampleBillModel(
            id=uuid4(),
            client_id=client_id,
            external_id=record.get("external_id"),
            bill_number=record.get("bill_number"),
            vendor_id=vendor_id,
            project_id=project_id,
            amount=Decimal(str(record.get("amount", 0))),
            date=parse_date(record.get("date")) or datetime.now(UTC).replace(tzinfo=None),
            due_date=parse_date(record.get("due_date")),
            paid_on_date=parse_date(record.get("paid_on_date")),
            description=record.get("description"),
            currency=record.get("currency", "USD"),
            status=record.get("status", "pending"),
            line_items=record.get("line_items"),
        )
        session.add(bill)
        return {"action": "created"}

    async def update(
        self,
        session: AsyncSession,
        existing: SampleBillModel,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        """Update an existing bill record."""
        date_fields = {"date", "due_date", "paid_on_date"}
        decimal_fields = {"amount"}
        skip_fields = {"id", "client_id", "vendor", "project", "vendor_id", "project_id"}

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

        # Handle vendor_id and project_id from nested objects or direct values
        if "vendor" in record and record["vendor"].get("id"):
            existing.vendor_id = UUID(record["vendor"]["id"])  # type: ignore[assignment]
        elif record.get("vendor_id"):
            existing.vendor_id = (
                UUID(record["vendor_id"])
                if isinstance(record["vendor_id"], str)
                else record["vendor_id"]
            )

        if "project" in record and record["project"].get("id"):
            existing.project_id = UUID(record["project"]["id"])  # type: ignore[assignment]
        elif record.get("project_id"):
            existing.project_id = (
                UUID(record["project_id"])
                if isinstance(record["project_id"], str)
                else record["project_id"]
            )

        existing.updated_at = datetime.now(UTC).replace(tzinfo=None)  # type: ignore[assignment]
        return {"action": "updated"}

    async def delete(
        self,
        session: AsyncSession,
        existing: SampleBillModel,
    ) -> dict[str, Any]:
        """Delete a bill record."""
        await session.delete(existing)
        return {"action": "deleted"}

    def get_required_fields(self) -> list[str]:
        """Return required fields for bill import."""
        return ["amount", "date"]
