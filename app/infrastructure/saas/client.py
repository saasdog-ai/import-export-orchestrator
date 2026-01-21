"""Mock SaaS API client for import/export operations."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domain.entities import ExportEntity, ImportConfig, ImportMode, RecordAction
from app.infrastructure.db.database import Database
from app.infrastructure.db.models import (
    SampleBillModel,
    SampleInvoiceModel,
    SampleProjectModel,
    SampleVendorModel,
)

# Column/key name for per-record actions
ACTION_KEY = "_action"

logger = get_logger(__name__)


def _parse_date(value: Any) -> datetime | None:
    """Parse date from string, datetime, or return None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        # Convert to naive UTC if timezone-aware
        if value.tzinfo is not None:
            return value.astimezone(UTC).replace(tzinfo=None)
        return value
    if isinstance(value, str):
        try:
            # Try ISO format first (handles both with and without timezone)
            if value.endswith("Z"):
                value = value[:-1] + "+00:00"
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is not None:
                return dt.astimezone(UTC).replace(tzinfo=None)
            return dt
        except (ValueError, TypeError):
            # Try parsing as date only (YYYY-MM-DD)
            try:
                dt = datetime.strptime(value, "%Y-%m-%d")
                return dt
            except ValueError:
                logger.warning(f"Failed to parse date: {value}")
                return None
    return None


class SaaSApiClientInterface:
    """Interface for SaaS API client."""

    async def fetch_data(
        self,
        entity: ExportEntity,
        client_id: UUID,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch data from SaaS API for a specific client.

        Args:
            entity: The entity type to fetch
            client_id: The client ID to filter data by (security: only return data owned by this client)
            filters: Optional additional filters to apply

        Returns:
            List of records owned by the specified client
        """
        raise NotImplementedError

    async def import_data(
        self, config: ImportConfig, client_id: UUID, data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Import data to SaaS API for a specific client.

        Args:
            config: Import configuration
            client_id: The client ID to associate imported records with (security: ensures data ownership)
            data: List of records to import

        Returns:
            Import result with counts and errors
        """
        raise NotImplementedError


class MockSaaSApiClient(SaaSApiClientInterface):
    """Mock implementation of SaaS API client using database tables for sample data."""

    def __init__(self, db: Database):
        """
        Initialize mock client with database connection.

        Args:
            db: Database instance for querying sample data tables
        """
        self.db = db

    def _model_to_dict(self, model: Any, include_relations: bool = False) -> dict[str, Any]:
        """Convert SQLAlchemy model to dictionary."""
        result = {}
        for column in model.__table__.columns:
            value = getattr(model, column.name)
            # Convert UUID to string
            if isinstance(value, UUID):
                value = str(value)
            # Convert Decimal to float
            elif isinstance(value, Decimal):
                value = float(value)
            # Convert datetime to ISO string
            elif isinstance(value, datetime):
                value = value.isoformat() + "Z"
            result[column.name] = value

        # Add client_id as string for compatibility
        result["client_id"] = str(result.get("client_id", ""))

        # Add id as string for compatibility
        if "id" in result:
            result["id"] = str(result["id"])

        # Map database field names to schema field names for compatibility
        # This allows the query engine to use schema field names while the DB uses different names
        field_mapping = {
            "email_address": "email",  # Vendor/Contact email
            "total_amount": "amount",  # Invoice amount
            "issue_date": "date",  # Invoice date
        }

        for db_field, schema_field in field_mapping.items():
            if db_field in result:
                result[schema_field] = result[db_field]

        return result

    async def _fetch_vendors(self, client_id: UUID) -> list[dict[str, Any]]:
        """Fetch vendors from database."""
        async with self.db.transaction() as session:
            result = await session.execute(
                select(SampleVendorModel).where(SampleVendorModel.client_id == client_id)
            )
            vendors = result.scalars().all()
            return [self._model_to_dict(v) for v in vendors]

    async def _fetch_projects(self, client_id: UUID) -> list[dict[str, Any]]:
        """Fetch projects from database."""
        async with self.db.transaction() as session:
            result = await session.execute(
                select(SampleProjectModel).where(SampleProjectModel.client_id == client_id)
            )
            projects = result.scalars().all()
            return [self._model_to_dict(p) for p in projects]

    async def _fetch_bills(self, client_id: UUID) -> list[dict[str, Any]]:
        """Fetch bills from database with nested vendor and project data."""
        async with self.db.transaction() as session:
            result = await session.execute(
                select(SampleBillModel)
                .where(SampleBillModel.client_id == client_id)
                .order_by(SampleBillModel.date.desc())
            )
            bills = result.scalars().all()

            bills_dict = []
            for bill in bills:
                bill_dict = self._model_to_dict(bill)

                # Add nested vendor if vendor_id exists
                if bill.vendor_id:
                    vendor_result = await session.execute(
                        select(SampleVendorModel).where(SampleVendorModel.id == bill.vendor_id)
                    )
                    vendor = vendor_result.scalar_one_or_none()
                    if vendor:
                        bill_dict["vendor"] = self._model_to_dict(vendor)
                        bill_dict["vendor_id"] = str(bill.vendor_id)

                # Add nested project if project_id exists
                if bill.project_id:
                    project_result = await session.execute(
                        select(SampleProjectModel).where(SampleProjectModel.id == bill.project_id)
                    )
                    project = project_result.scalar_one_or_none()
                    if project:
                        bill_dict["project"] = self._model_to_dict(project)
                        bill_dict["project_id"] = str(bill.project_id)

                bills_dict.append(bill_dict)

            return bills_dict

    async def _fetch_invoices(self, client_id: UUID) -> list[dict[str, Any]]:
        """Fetch invoices from database with nested contact (vendor) data."""
        async with self.db.transaction() as session:
            result = await session.execute(
                select(SampleInvoiceModel)
                .where(SampleInvoiceModel.client_id == client_id)
                .order_by(
                    SampleInvoiceModel.issue_date.desc()
                    if SampleInvoiceModel.issue_date
                    else SampleInvoiceModel.created_at.desc()
                )
            )
            invoices = result.scalars().all()

            invoices_dict = []
            for invoice in invoices:
                invoice_dict = self._model_to_dict(invoice)

                # Add nested vendor/contact if contact_id exists
                if invoice.contact_id:
                    vendor_result = await session.execute(
                        select(SampleVendorModel).where(SampleVendorModel.id == invoice.contact_id)
                    )
                    vendor = vendor_result.scalar_one_or_none()
                    if vendor:
                        invoice_dict["vendor"] = self._model_to_dict(vendor)
                        invoice_dict["contact_id"] = str(invoice.contact_id)

                invoices_dict.append(invoice_dict)

            return invoices_dict

    async def fetch_data(
        self,
        entity: ExportEntity,
        client_id: UUID,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch data from database for an entity, filtered by client_id for security.

        Only returns records that belong to the specified client_id.
        This ensures multi-tenant data isolation.
        """
        # Log external service call input
        filter_summary = "present" if filters else "none"
        logger.info(
            f"SaaS API fetch_data request: entity={entity.value}, client_id={client_id}, filters={filter_summary}"
        )

        # Fetch data based on entity type
        if entity == ExportEntity.VENDOR:
            data = await self._fetch_vendors(client_id)
        elif entity == ExportEntity.PROJECT:
            data = await self._fetch_projects(client_id)
        elif entity == ExportEntity.BILL:
            data = await self._fetch_bills(client_id)
        elif entity == ExportEntity.INVOICE:
            data = await self._fetch_invoices(client_id)
        else:
            data = []

        # Apply additional filters if provided (simplified mock filtering)
        if filters:
            # In real implementation, would apply actual filtering
            pass

        # Log external service call output
        logger.info(
            f"SaaS API fetch_data response: entity={entity.value}, client_id={client_id}, "
            f"record_count={len(data)}"
        )

        return data

    async def import_data(
        self, config: ImportConfig, client_id: UUID, data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Import data to database with detailed error reporting.

        SECURITY: All imported records are automatically associated with the specified client_id.
        This ensures data ownership and prevents cross-client data leakage.

        Import modes (global or per-record via _action column):
        - CREATE: Insert only - fail if external_id already exists
        - UPDATE: Update only - skip if external_id not found
        - UPSERT: Create or update based on external_id match
        - DELETE: Remove record matching external_id (per-record only)

        Returns count of imported/updated/deleted records and any errors with row information.
        """
        global_import_mode = config.import_mode
        match_key = config.match_key

        # Check if data uses per-record actions
        has_per_record_actions = data and ACTION_KEY in data[0]

        # Log external service call input
        logger.info(
            f"SaaS API import_data request: entity={config.entity.value}, client_id={client_id}, "
            f"record_count={len(data)}, source={config.source}, "
            f"mode={'per-record' if has_per_record_actions else global_import_mode.value}, "
            f"match_key={match_key}"
        )

        entity = config.entity
        imported_count = 0
        updated_count = 0
        deleted_count = 0
        skipped_count = 0
        failed_count = 0
        errors: list[dict[str, Any]] = []

        async with self.db.transaction() as session:
            # Track row number for error reporting (1-based for user-friendly reporting)
            for row_num, record in enumerate(data, start=1):
                try:
                    # Determine the action for this record
                    if has_per_record_actions:
                        action_str = record.pop(ACTION_KEY, None)
                        record_action = RecordAction.from_string(action_str) if action_str else None
                        if record_action is None:
                            errors.append(
                                {
                                    "row": row_num,
                                    "field": ACTION_KEY,
                                    "message": f"Invalid action '{action_str}'",
                                }
                            )
                            failed_count += 1
                            continue
                        # Convert RecordAction to ImportMode for non-DELETE actions
                        if record_action == RecordAction.DELETE:
                            import_mode = None  # Special handling for delete
                            is_delete = True
                        else:
                            import_mode = ImportMode(record_action.value)
                            is_delete = False
                    else:
                        import_mode = global_import_mode
                        is_delete = False

                    # Handle DELETE action
                    if is_delete:
                        match_value = record.get(match_key)
                        if not match_value:
                            errors.append(
                                {
                                    "row": row_num,
                                    "field": match_key,
                                    "message": f"Match key '{match_key}' required for DELETE",
                                }
                            )
                            failed_count += 1
                            continue

                        delete_result = await self._delete_record(
                            session, entity, client_id, match_key, match_value
                        )
                        if delete_result["action"] == "deleted":
                            deleted_count += 1
                        elif delete_result["action"] == "skipped":
                            skipped_count += 1
                        else:
                            failed_count += 1
                            errors.append(
                                {
                                    "row": row_num,
                                    "message": delete_result.get("error", "Delete failed"),
                                }
                            )
                        continue

                    # Validate required fields for non-DELETE actions
                    required_fields = (
                        ["amount", "date"]
                        if entity in [ExportEntity.BILL, ExportEntity.INVOICE]
                        else ["name"]
                        if entity == ExportEntity.VENDOR
                        else []
                    )
                    missing_required = False
                    for field in required_fields:
                        if (
                            field not in record
                            or record[field] is None
                            or (isinstance(record[field], str) and record[field].strip() == "")
                        ):
                            errors.append(
                                {
                                    "row": row_num,
                                    "field": field,
                                    "message": f"Required field '{field}' is missing or empty",
                                }
                            )
                            failed_count += 1
                            missing_required = True
                            break

                    if missing_required:
                        continue

                    # For UPDATE mode, require match_key to be present
                    if import_mode == ImportMode.UPDATE:
                        match_value = record.get(match_key)
                        if not match_value or (
                            isinstance(match_value, str) and not match_value.strip()
                        ):
                            errors.append(
                                {
                                    "row": row_num,
                                    "field": match_key,
                                    "message": f"Match key '{match_key}' is required for UPDATE mode",
                                }
                            )
                            failed_count += 1
                            continue

                    # SECURITY: Ensure all records have the correct client_id
                    record["client_id"] = client_id

                    # At this point, import_mode is guaranteed to be set (DELETE was handled above)
                    assert import_mode is not None

                    # Handle different entity types
                    if entity == ExportEntity.VENDOR:
                        import_result = await self._import_vendor(
                            session, record, client_id, import_mode, match_key
                        )
                    elif entity == ExportEntity.PROJECT:
                        import_result = await self._import_project(
                            session, record, client_id, import_mode, match_key
                        )
                    elif entity == ExportEntity.BILL:
                        import_result = await self._import_bill(
                            session, record, client_id, import_mode, match_key
                        )
                    elif entity == ExportEntity.INVOICE:
                        import_result = await self._import_invoice(
                            session, record, client_id, import_mode, match_key
                        )
                    else:
                        errors.append(
                            {
                                "row": row_num,
                                "message": f"Unsupported entity type: {entity.value}",
                            }
                        )
                        failed_count += 1
                        continue

                    if import_result["action"] == "created":
                        imported_count += 1
                    elif import_result["action"] == "updated":
                        updated_count += 1
                    elif import_result["action"] == "skipped":
                        skipped_count += 1
                    else:
                        failed_count += 1
                        errors.append(
                            {"row": row_num, "message": import_result.get("error", "Unknown error")}
                        )

                except Exception as e:
                    error_msg = f"Failed to import record: {str(e)}"
                    logger.error(f"Row {row_num}: {error_msg}", exc_info=True)
                    errors.append({"row": row_num, "message": error_msg})
                    failed_count += 1

            await session.commit()

        mode_str = "per-record" if has_per_record_actions else global_import_mode.value
        result: dict[str, Any] = {
            "imported_count": imported_count,
            "updated_count": updated_count,
            "deleted_count": deleted_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "entity": config.entity.value,
            "import_mode": mode_str,
        }

        # Include errors if any
        if errors:
            result["errors"] = errors

        # Log external service call output
        logger.info(
            f"SaaS API import_data response: entity={config.entity.value}, mode={mode_str}, "
            f"imported={imported_count}, updated={updated_count}, deleted={deleted_count}, "
            f"skipped={skipped_count}, failed={failed_count}, error_count={len(errors)}"
        )

        return result

    async def _import_vendor(
        self,
        session: AsyncSession,
        record: dict[str, Any],
        client_id: UUID,
        import_mode: ImportMode,
        match_key: str,
    ) -> dict[str, Any]:
        """Import a vendor record with support for CREATE/UPDATE/UPSERT modes."""
        # Try to find existing record by match_key (e.g., external_id)
        match_value = record.get(match_key)
        existing = None

        if match_value and match_key == "external_id":
            result = await session.execute(
                select(SampleVendorModel).where(
                    SampleVendorModel.client_id == client_id,
                    SampleVendorModel.external_id == match_value,
                )
            )
            existing = result.scalar_one_or_none()
        elif match_value and match_key == "id":
            # Fallback to id-based matching for backward compatibility
            try:
                vendor_id = UUID(match_value)
                result = await session.execute(
                    select(SampleVendorModel).where(
                        SampleVendorModel.id == vendor_id,
                        SampleVendorModel.client_id == client_id,
                    )
                )
                existing = result.scalar_one_or_none()
            except ValueError:
                return {"action": "failed", "error": f"Invalid UUID: {match_value}"}

        # Handle based on import mode
        if import_mode == ImportMode.CREATE:
            if existing:
                return {
                    "action": "failed",
                    "error": f"Record with {match_key}='{match_value}' already exists",
                }
            # Create new
        elif import_mode == ImportMode.UPDATE:
            if not existing:
                return {"action": "skipped"}  # No matching record to update
            # Update existing
            for key, value in record.items():
                if key not in ["id", "client_id"] and hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = datetime.now(UTC).replace(tzinfo=None)  # type: ignore[assignment]
            return {"action": "updated"}
        elif import_mode == ImportMode.UPSERT:
            if existing:
                # Update existing
                for key, value in record.items():
                    if key not in ["id", "client_id"] and hasattr(existing, key):
                        setattr(existing, key, value)
                existing.updated_at = datetime.now(UTC).replace(tzinfo=None)  # type: ignore[assignment]
                return {"action": "updated"}
            # Create new (fall through to creation below)

        # Create new record
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

    async def _import_project(
        self,
        session: AsyncSession,
        record: dict[str, Any],
        client_id: UUID,
        import_mode: ImportMode,
        match_key: str,
    ) -> dict[str, Any]:
        """Import a project record with support for CREATE/UPDATE/UPSERT modes."""
        # Try to find existing record by match_key (e.g., external_id)
        match_value = record.get(match_key)
        existing = None

        if match_value and match_key == "external_id":
            result = await session.execute(
                select(SampleProjectModel).where(
                    SampleProjectModel.client_id == client_id,
                    SampleProjectModel.external_id == match_value,
                )
            )
            existing = result.scalar_one_or_none()
        elif match_value and match_key == "id":
            # Fallback to id-based matching for backward compatibility
            try:
                project_id = UUID(match_value)
                result = await session.execute(
                    select(SampleProjectModel).where(
                        SampleProjectModel.id == project_id,
                        SampleProjectModel.client_id == client_id,
                    )
                )
                existing = result.scalar_one_or_none()
            except ValueError:
                return {"action": "failed", "error": f"Invalid UUID: {match_value}"}

        # Handle based on import mode
        if import_mode == ImportMode.CREATE:
            if existing:
                return {
                    "action": "failed",
                    "error": f"Record with {match_key}='{match_value}' already exists",
                }
            # Create new
        elif import_mode == ImportMode.UPDATE:
            if not existing:
                return {"action": "skipped"}  # No matching record to update
            # Update existing
            self._update_project_fields(existing, record)
            return {"action": "updated"}
        elif import_mode == ImportMode.UPSERT:
            if existing:
                # Update existing
                self._update_project_fields(existing, record)
                return {"action": "updated"}
            # Create new (fall through to creation below)

        # Create new record
        project = SampleProjectModel(
            id=uuid4(),
            client_id=client_id,
            external_id=record.get("external_id"),
            code=record.get("code"),
            name=record.get("name", ""),
            description=record.get("description"),
            status=record.get("status", "active"),
            start_date=_parse_date(record.get("start_date")),
            end_date=_parse_date(record.get("end_date")),
            budget=record.get("budget"),
            currency=record.get("currency", "USD"),
        )
        session.add(project)
        return {"action": "created"}

    def _update_project_fields(self, existing: SampleProjectModel, record: dict[str, Any]) -> None:
        """Update project fields from record data."""
        date_fields = {"start_date", "end_date"}
        decimal_fields = {"budget"}
        skip_fields = {"id", "client_id"}

        for key, value in record.items():
            if key in skip_fields or not hasattr(existing, key):
                continue
            if value is None or value == "":
                continue

            if key in date_fields:
                setattr(existing, key, _parse_date(value))
            elif key in decimal_fields:
                setattr(existing, key, Decimal(str(value)) if value else None)
            else:
                setattr(existing, key, value)

        existing.updated_at = datetime.now(UTC).replace(tzinfo=None)  # type: ignore[assignment]

    async def _import_bill(
        self,
        session: AsyncSession,
        record: dict[str, Any],
        client_id: UUID,
        import_mode: ImportMode,
        match_key: str,
    ) -> dict[str, Any]:
        """Import a bill record with support for CREATE/UPDATE/UPSERT modes."""
        # Try to find existing record by match_key (e.g., external_id)
        match_value = record.get(match_key)
        existing = None

        if match_value and match_key == "external_id":
            result = await session.execute(
                select(SampleBillModel).where(
                    SampleBillModel.client_id == client_id,
                    SampleBillModel.external_id == match_value,
                )
            )
            existing = result.scalar_one_or_none()
        elif match_value and match_key == "id":
            # Fallback to id-based matching for backward compatibility
            try:
                bill_id = UUID(match_value)
                result = await session.execute(
                    select(SampleBillModel).where(
                        SampleBillModel.id == bill_id,
                        SampleBillModel.client_id == client_id,
                    )
                )
                existing = result.scalar_one_or_none()
            except ValueError:
                return {"action": "failed", "error": f"Invalid UUID: {match_value}"}

        # Handle based on import mode
        if import_mode == ImportMode.CREATE:
            if existing:
                return {
                    "action": "failed",
                    "error": f"Record with {match_key}='{match_value}' already exists",
                }
            # Create new
        elif import_mode == ImportMode.UPDATE:
            if not existing:
                return {"action": "skipped"}  # No matching record to update
            # Update existing
            self._update_bill_fields(existing, record)
            return {"action": "updated"}
        elif import_mode == ImportMode.UPSERT:
            if existing:
                # Update existing
                self._update_bill_fields(existing, record)
                return {"action": "updated"}
            # Create new (fall through to creation below)

        # Create new record
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
            date=_parse_date(record.get("date")) or datetime.now(UTC).replace(tzinfo=None),
            due_date=_parse_date(record.get("due_date")),
            paid_on_date=_parse_date(record.get("paid_on_date")),
            description=record.get("description"),
            currency=record.get("currency", "USD"),
            status=record.get("status", "pending"),
            line_items=record.get("line_items"),
        )
        session.add(bill)
        return {"action": "created"}

    def _update_bill_fields(self, existing: SampleBillModel, record: dict[str, Any]) -> None:
        """Update bill fields from record data."""
        # Fields that need special type conversion
        date_fields = {"date", "due_date", "paid_on_date"}
        decimal_fields = {"amount"}
        skip_fields = {"id", "client_id", "vendor", "project", "vendor_id", "project_id"}

        for key, value in record.items():
            if key in skip_fields or not hasattr(existing, key):
                continue
            if value is None or value == "":
                continue

            # Convert dates
            if key in date_fields:
                setattr(existing, key, _parse_date(value))
            # Convert decimals
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

    async def _import_invoice(
        self,
        session: AsyncSession,
        record: dict[str, Any],
        client_id: UUID,
        import_mode: ImportMode,
        match_key: str,
    ) -> dict[str, Any]:
        """Import an invoice record with support for CREATE/UPDATE/UPSERT modes."""
        # Try to find existing record by match_key (e.g., external_id)
        match_value = record.get(match_key)
        existing = None

        if match_value and match_key == "external_id":
            result = await session.execute(
                select(SampleInvoiceModel).where(
                    SampleInvoiceModel.client_id == client_id,
                    SampleInvoiceModel.external_id == match_value,
                )
            )
            existing = result.scalar_one_or_none()
        elif match_value and match_key == "id":
            # Fallback to id-based matching for backward compatibility
            try:
                invoice_id = UUID(match_value)
                result = await session.execute(
                    select(SampleInvoiceModel).where(
                        SampleInvoiceModel.id == invoice_id,
                        SampleInvoiceModel.client_id == client_id,
                    )
                )
                existing = result.scalar_one_or_none()
            except ValueError:
                return {"action": "failed", "error": f"Invalid UUID: {match_value}"}

        # Handle based on import mode
        if import_mode == ImportMode.CREATE:
            if existing:
                return {
                    "action": "failed",
                    "error": f"Record with {match_key}='{match_value}' already exists",
                }
            # Create new
        elif import_mode == ImportMode.UPDATE:
            if not existing:
                return {"action": "skipped"}  # No matching record to update
            # Update existing
            self._update_invoice_fields(existing, record)
            return {"action": "updated"}
        elif import_mode == ImportMode.UPSERT:
            if existing:
                # Update existing
                self._update_invoice_fields(existing, record)
                return {"action": "updated"}
            # Create new (fall through to creation below)

        # Create new record
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
            issue_date=_parse_date(record.get("issue_date") or record.get("date")),
            due_date=_parse_date(record.get("due_date")),
            paid_on_date=_parse_date(record.get("paid_on_date")),
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

    def _update_invoice_fields(self, existing: SampleInvoiceModel, record: dict[str, Any]) -> None:
        """Update invoice fields from record data."""
        # Map schema field names to database field names
        if "amount" in record and "total_amount" not in record:
            record["total_amount"] = record["amount"]
        if "date" in record and "issue_date" not in record:
            record["issue_date"] = record["date"]

        # Fields that need special type conversion
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
                setattr(existing, key, _parse_date(value))
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
            existing.issue_date = _parse_date(record["issue_date"])  # type: ignore[assignment]
        elif "date" in record:
            existing.issue_date = _parse_date(record["date"])  # type: ignore[assignment]
        # Handle contact_id from nested objects
        if "vendor" in record and record["vendor"].get("id"):
            existing.contact_id = UUID(record["vendor"]["id"])  # type: ignore[assignment]
        elif "contact_id" in record:
            existing.contact_id = UUID(record["contact_id"])  # type: ignore[assignment]
        existing.updated_at = datetime.now(UTC).replace(tzinfo=None)  # type: ignore[assignment]

    async def _delete_record(
        self,
        session: AsyncSession,
        entity: ExportEntity,
        client_id: UUID,
        match_key: str,
        match_value: Any,
    ) -> dict[str, Any]:
        """Delete a record by match key.

        Args:
            session: Database session
            entity: Entity type
            client_id: Client ID for security filtering
            match_key: Field to match on (e.g., 'external_id')
            match_value: Value to match

        Returns:
            Dict with 'action' key: 'deleted', 'skipped', or 'failed'
        """
        model_map = {
            ExportEntity.VENDOR: SampleVendorModel,
            ExportEntity.PROJECT: SampleProjectModel,
            ExportEntity.BILL: SampleBillModel,
            ExportEntity.INVOICE: SampleInvoiceModel,
        }

        model = model_map.get(entity)
        if not model:
            return {"action": "failed", "error": f"Unsupported entity type: {entity.value}"}

        # Find the record
        existing = None
        if match_key == "external_id":
            result = await session.execute(
                select(model).where(
                    model.client_id == client_id,  # type: ignore[attr-defined]
                    model.external_id == match_value,  # type: ignore[attr-defined]
                )
            )
            existing = result.scalar_one_or_none()
        elif match_key == "id":
            try:
                record_id = UUID(match_value)
                result = await session.execute(
                    select(model).where(
                        model.id == record_id,  # type: ignore[attr-defined]
                        model.client_id == client_id,  # type: ignore[attr-defined]
                    )
                )
                existing = result.scalar_one_or_none()
            except ValueError:
                return {"action": "failed", "error": f"Invalid UUID: {match_value}"}

        if not existing:
            return {"action": "skipped"}  # No matching record to delete

        await session.delete(existing)
        return {"action": "deleted"}
