"""Base SaaS API client with generic import/export orchestration."""

from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domain.entities import ExportEntity, ImportConfig, ImportMode, RecordAction
from app.infrastructure.db.database import Database

# Column/key name for per-record actions
ACTION_KEY = "_action"

logger = get_logger(__name__)


class EntityHandler(Protocol):
    """Protocol for entity-specific import/export handlers."""

    async def fetch(self, session: AsyncSession, client_id: UUID) -> list[dict[str, Any]]:
        """Fetch all records for this entity owned by client_id."""
        ...

    async def find_existing(
        self,
        session: AsyncSession,
        client_id: UUID,
        match_key: str,
        match_value: Any,
    ) -> Any | None:
        """Find an existing record by match key."""
        ...

    async def create(
        self,
        session: AsyncSession,
        record: dict[str, Any],
        client_id: UUID,
    ) -> dict[str, Any]:
        """Create a new record. Returns {"action": "created"}."""
        ...

    async def update(
        self,
        session: AsyncSession,
        existing: Any,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        """Update an existing record. Returns {"action": "updated"}."""
        ...

    async def delete(
        self,
        session: AsyncSession,
        existing: Any,
    ) -> dict[str, Any]:
        """Delete a record. Returns {"action": "deleted"}."""
        ...

    def get_required_fields(self) -> list[str]:
        """Return the list of required field names for import validation."""
        ...


class BaseSaaSApiClient:
    """Base SaaS API client with generic import/export orchestration.

    Subclasses register EntityHandler instances for each supported entity.
    The generic fetch_data() and import_data() methods dispatch to the
    appropriate handler.
    """

    def __init__(self, db: Database) -> None:
        self.db = db
        self._handlers: dict[ExportEntity, EntityHandler] = {}

    def register_handler(self, entity: ExportEntity, handler: EntityHandler) -> None:
        """Register a handler for a specific entity type."""
        self._handlers[entity] = handler

    # ------------------------------------------------------------------
    # fetch_data — dispatches to handler.fetch()
    # ------------------------------------------------------------------

    async def fetch_data(
        self,
        entity: ExportEntity,
        client_id: UUID,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch data by dispatching to the registered entity handler."""
        filter_summary = "present" if filters else "none"
        logger.info(
            f"SaaS API fetch_data request: entity={entity.value}, "
            f"client_id={client_id}, filters={filter_summary}"
        )

        handler = self._handlers.get(entity)
        if handler is None:
            logger.warning(f"No handler registered for entity: {entity.value}")
            return []

        async with self.db.transaction() as session:
            data = await handler.fetch(session, client_id)

        logger.info(
            f"SaaS API fetch_data response: entity={entity.value}, "
            f"client_id={client_id}, record_count={len(data)}"
        )
        return data

    # ------------------------------------------------------------------
    # import_data — generic orchestration loop
    # ------------------------------------------------------------------

    async def import_data(
        self, config: ImportConfig, client_id: UUID, data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Import data with detailed error reporting.

        Orchestrates the full import loop: action routing, required-field
        validation, match-key lookup, and per-record create/update/delete
        via the registered entity handler.
        """
        global_import_mode = config.import_mode
        match_key = config.match_key
        entity = config.entity

        has_per_record_actions = bool(data) and ACTION_KEY in data[0]

        logger.info(
            f"SaaS API import_data request: entity={entity.value}, client_id={client_id}, "
            f"record_count={len(data)}, source={config.source}, "
            f"mode={'per-record' if has_per_record_actions else global_import_mode.value}, "
            f"match_key={match_key}"
        )

        handler = self._handlers.get(entity)
        if handler is None:
            return {
                "imported_count": 0,
                "updated_count": 0,
                "deleted_count": 0,
                "skipped_count": 0,
                "failed_count": len(data),
                "entity": entity.value,
                "import_mode": global_import_mode.value,
                "errors": [{"row": 0, "message": f"No handler for entity: {entity.value}"}],
            }

        imported_count = 0
        updated_count = 0
        deleted_count = 0
        skipped_count = 0
        failed_count = 0
        errors: list[dict[str, Any]] = []

        async with self.db.transaction() as session:
            for row_num, record in enumerate(data, start=1):
                try:
                    # Determine action for this record
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
                        if record_action == RecordAction.DELETE:
                            import_mode = None
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

                        existing = await handler.find_existing(
                            session, client_id, match_key, match_value
                        )
                        if not existing:
                            skipped_count += 1
                            continue
                        delete_result = await handler.delete(session, existing)
                        if delete_result["action"] == "deleted":
                            deleted_count += 1
                        else:
                            failed_count += 1
                            errors.append(
                                {
                                    "row": row_num,
                                    "message": delete_result.get("error", "Delete failed"),
                                }
                            )
                        continue

                    # Validate required fields
                    required_fields = handler.get_required_fields()
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

                    assert import_mode is not None

                    # Find existing record
                    match_value = record.get(match_key)
                    existing = None
                    if match_value:
                        existing = await handler.find_existing(
                            session, client_id, match_key, match_value
                        )

                    # Handle import modes
                    if import_mode == ImportMode.CREATE:
                        if existing:
                            errors.append(
                                {
                                    "row": row_num,
                                    "message": f"Record with {match_key}='{match_value}' already exists",
                                }
                            )
                            failed_count += 1
                            continue
                        import_result = await handler.create(session, record, client_id)
                    elif import_mode == ImportMode.UPDATE:
                        if not existing:
                            skipped_count += 1
                            continue
                        import_result = await handler.update(session, existing, record)
                    elif import_mode == ImportMode.UPSERT:
                        if existing:
                            import_result = await handler.update(session, existing, record)
                        else:
                            import_result = await handler.create(session, record, client_id)
                    else:
                        errors.append(
                            {"row": row_num, "message": f"Unsupported import mode: {import_mode}"}
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
            "entity": entity.value,
            "import_mode": mode_str,
        }
        if errors:
            result["errors"] = errors

        logger.info(
            f"SaaS API import_data response: entity={entity.value}, mode={mode_str}, "
            f"imported={imported_count}, updated={updated_count}, deleted={deleted_count}, "
            f"skipped={skipped_count}, failed={failed_count}, error_count={len(errors)}"
        )

        return result
