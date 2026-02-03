"""Invoice entity handler for import/export operations."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.db.models import (
    SampleInvoiceModel,
    SampleVendorModel,
)
from app.infrastructure.saas.utils import model_to_dict, parse_date

# Column map for SQL pushdown (includes relationship fields via dot notation)
_COLUMN_MAP: dict[str, Column] = {
    "id": SampleInvoiceModel.id,
    "external_id": SampleInvoiceModel.external_id,
    "invoice_number": SampleInvoiceModel.invoice_number,
    "contact_id": SampleInvoiceModel.contact_id,
    "issue_date": SampleInvoiceModel.issue_date,
    "date": SampleInvoiceModel.issue_date,
    "due_date": SampleInvoiceModel.due_date,
    "paid_on_date": SampleInvoiceModel.paid_on_date,
    "memo": SampleInvoiceModel.memo,
    "currency": SampleInvoiceModel.currency,
    "exchange_rate": SampleInvoiceModel.exchange_rate,
    "sub_total": SampleInvoiceModel.sub_total,
    "total_tax_amount": SampleInvoiceModel.total_tax_amount,
    "total_amount": SampleInvoiceModel.total_amount,
    "amount": SampleInvoiceModel.total_amount,
    "balance": SampleInvoiceModel.balance,
    "status": SampleInvoiceModel.status,
    "created_at": SampleInvoiceModel.created_at,
    "updated_at": SampleInvoiceModel.updated_at,
    # Relationship columns
    "vendor.name": SampleVendorModel.name,
    "vendor.email_address": SampleVendorModel.email_address,
    "vendor.email": SampleVendorModel.email_address,
    "vendor.id": SampleVendorModel.id,
    "vendor.status": SampleVendorModel.status,
}


class InvoiceHandler:
    """Handler for invoice fetch, create, update, and delete operations."""

    def build_query(self, client_id: UUID) -> Select:
        """Return base SELECT with eager-loaded relationships, filtered by client_id."""
        return (
            select(SampleInvoiceModel)
            .where(SampleInvoiceModel.client_id == client_id)
            .options(selectinload(SampleInvoiceModel.contact))
        )

    def get_column(self, field_path: str) -> Column | None:
        """Resolve field path to SQLAlchemy column."""
        return _COLUMN_MAP.get(field_path)

    async def fetch(self, session: AsyncSession, client_id: UUID) -> list[dict[str, Any]]:
        """Fetch invoices from database with nested contact (vendor) data."""
        result = await session.execute(
            select(SampleInvoiceModel)
            .where(SampleInvoiceModel.client_id == client_id)
            .order_by(
                SampleInvoiceModel.issue_date.desc()
                if SampleInvoiceModel.issue_date
                else SampleInvoiceModel.created_at.desc()
            )
            .options(selectinload(SampleInvoiceModel.contact))
        )
        invoices = result.scalars().all()

        invoices_dict = []
        for invoice in invoices:
            invoice_dict = model_to_dict(invoice)

            if invoice.contact:
                invoice_dict["vendor"] = model_to_dict(invoice.contact)
                invoice_dict["contact_id"] = str(invoice.contact_id)

            invoices_dict.append(invoice_dict)

        return invoices_dict

    async def find_existing(
        self,
        session: AsyncSession,
        client_id: UUID,
        match_key: str,
        match_value: Any,
    ) -> SampleInvoiceModel | None:
        """Find an existing invoice by match key."""
        if match_key == "external_id":
            result = await session.execute(
                select(SampleInvoiceModel).where(
                    SampleInvoiceModel.client_id == client_id,
                    SampleInvoiceModel.external_id == match_value,
                )
            )
            return result.scalar_one_or_none()
        elif match_key == "id":
            try:
                invoice_id = UUID(match_value)
                result = await session.execute(
                    select(SampleInvoiceModel).where(
                        SampleInvoiceModel.id == invoice_id,
                        SampleInvoiceModel.client_id == client_id,
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
        """Create a new invoice record."""
        contact_id = None
        if record.get("contact_id"):
            contact_id = UUID(record["contact_id"])
        elif record.get("vendor") and record["vendor"].get("id"):
            contact_id = UUID(record["vendor"]["id"])

        invoice = SampleInvoiceModel(
            id=uuid4(),
            client_id=client_id,
            external_id=record.get("external_id"),
            invoice_number=record.get("invoice_number"),
            contact_id=contact_id,
            issue_date=parse_date(record.get("issue_date") or record.get("date")),
            due_date=parse_date(record.get("due_date")),
            paid_on_date=parse_date(record.get("paid_on_date")),
            memo=record.get("memo") or record.get("description"),
            currency=record.get("currency", "USD"),
            exchange_rate=record.get("exchange_rate"),
            sub_total=Decimal(str(record.get("sub_total", 0))) if record.get("sub_total") else None,
            total_tax_amount=Decimal(str(record.get("total_tax_amount", 0)))
            if record.get("total_tax_amount")
            else None,
            total_amount=Decimal(str(record.get("total_amount", record.get("amount", 0)))),
            balance=Decimal(str(record.get("balance", 0))) if record.get("balance") else None,
            status=record.get("status", "DRAFT"),
            line_items=record.get("line_items"),
            tracking_categories=record.get("tracking_categories"),
        )
        session.add(invoice)
        return {"action": "created"}

    async def update(
        self,
        session: AsyncSession,
        existing: SampleInvoiceModel,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        """Update an existing invoice record."""
        # Map schema field names to database field names
        if "amount" in record and "total_amount" not in record:
            record["total_amount"] = record["amount"]
        if "date" in record and "issue_date" not in record:
            record["issue_date"] = record["date"]

        date_fields = {"issue_date", "due_date", "paid_on_date"}
        decimal_fields = {
            "total_amount",
            "sub_total",
            "total_tax_amount",
            "balance",
            "exchange_rate",
        }
        skip_fields = {"id", "client_id", "vendor", "contact", "amount", "date", "contact_id"}

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

        # Handle mapped fields
        if "total_amount" in record:
            existing.total_amount = Decimal(str(record["total_amount"]))  # type: ignore[assignment]
        elif "amount" in record:
            existing.total_amount = Decimal(str(record["amount"]))  # type: ignore[assignment]
        if "issue_date" in record:
            existing.issue_date = parse_date(record["issue_date"])  # type: ignore[assignment]
        elif "date" in record:
            existing.issue_date = parse_date(record["date"])  # type: ignore[assignment]
        # Handle contact_id from nested objects
        if "vendor" in record and record["vendor"].get("id"):
            existing.contact_id = UUID(record["vendor"]["id"])  # type: ignore[assignment]
        elif "contact_id" in record:
            existing.contact_id = UUID(record["contact_id"])  # type: ignore[assignment]
        existing.updated_at = datetime.now(UTC).replace(tzinfo=None)  # type: ignore[assignment]
        return {"action": "updated"}

    async def delete(
        self,
        session: AsyncSession,
        existing: SampleInvoiceModel,
    ) -> dict[str, Any]:
        """Delete an invoice record."""
        await session.delete(existing)
        return {"action": "deleted"}

    def get_required_fields(self) -> list[str]:
        """Return required fields for invoice import."""
        return ["amount", "date"]
