"""Mock SaaS API client for import/export operations."""

import json
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.core.config import get_settings
from app.core.logging import get_logger
from app.domain.entities import ExportEntity, ImportConfig

logger = get_logger(__name__)

settings = get_settings()


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
    """Mock implementation of SaaS API client with stateful data storage."""

    def __init__(self, data_file: str | None = None):
        """
        Initialize mock client with sample data.

        Args:
            data_file: Optional path to JSON file to load/save mock data.
                      If None, uses in-memory storage only.
        """
        self.data_file = data_file
        # Initialize _sample_data as empty dict first
        self._sample_data: dict[ExportEntity, list[dict[str, Any]]] = {}
        self._load_initial_data()

    def _load_initial_data(self):
        """Load initial sample data from file or create default."""
        if self.data_file and Path(self.data_file).exists():
            try:
                with open(self.data_file) as f:
                    self._sample_data = json.load(f)
                    # Convert entity keys back to ExportEntity enum
                    self._sample_data = {ExportEntity(k): v for k, v in self._sample_data.items()}
                logger.info(f"Loaded mock data from {self.data_file}")
            except Exception as e:
                logger.warning(
                    f"Failed to load data file {self.data_file}: {e}. Using default data."
                )
                self._create_default_data()
        else:
            self._create_default_data()

    def _create_default_data(self):
        """Create default sample data with client_id for multi-tenant security."""
        # Default client ID for development/testing
        default_client_id = "00000000-0000-0000-0000-000000000000"
        # Second client ID for testing multi-tenant isolation
        client_2_id = "11111111-1111-1111-1111-111111111111"

        # Create sample vendors and projects for client 1
        vendor_acme = {
            "id": str(uuid4()),
            "client_id": default_client_id,
            "name": "Acme Corp",
            "email": "contact@acme.com",
            "phone": "+1-555-0100",
            "address": "123 Main St",
            "created_at": "2024-01-01T08:00:00Z",
        }
        vendor_tech = {
            "id": str(uuid4()),
            "client_id": default_client_id,
            "name": "Tech Solutions Inc",
            "email": "info@techsolutions.com",
            "phone": "+1-555-0200",
            "address": "456 Tech Ave",
            "created_at": "2024-01-01T08:00:00Z",
        }
        project_alpha = {
            "id": str(uuid4()),
            "client_id": default_client_id,
            "code": "PROJ-001",
            "name": "Project Alpha",
            "description": "Main project",
            "status": "active",
            "created_at": "2024-01-01T08:00:00Z",
        }
        project_beta = {
            "id": str(uuid4()),
            "client_id": default_client_id,
            "code": "PROJ-002",
            "name": "Project Beta",
            "description": "Secondary project",
            "status": "active",
            "created_at": "2024-01-01T08:00:00Z",
        }

        # Create sample vendors and projects for client 2 (to test isolation)
        vendor_client2 = {
            "id": str(uuid4()),
            "client_id": client_2_id,
            "name": "Client 2 Vendor",
            "email": "vendor@client2.com",
            "phone": "+1-555-0300",
            "address": "789 Other St",
            "created_at": "2024-01-01T08:00:00Z",
        }
        project_client2 = {
            "id": str(uuid4()),
            "client_id": client_2_id,
            "code": "PROJ-C2-001",
            "name": "Client 2 Project",
            "description": "Client 2 project",
            "status": "active",
            "created_at": "2024-01-01T08:00:00Z",
        }

        # Populate with default data (client 1 owns most data)
        self._sample_data = {
            ExportEntity.BILL: [
                {
                    "id": str(uuid4()),
                    "client_id": default_client_id,
                    "amount": 1000.50,
                    "date": "2024-01-15",
                    "description": "Office supplies",
                    "vendor_id": vendor_acme["id"],
                    "project_id": project_alpha["id"],
                    "vendor": vendor_acme,  # Nested vendor for "vendor.name" field access
                    "project": project_alpha,  # Nested project for "project.code" field access
                    "status": "paid",
                    "created_at": "2024-01-15T10:00:00Z",
                },
                {
                    "id": str(uuid4()),
                    "client_id": default_client_id,
                    "amount": 2500.00,
                    "date": "2024-01-20",
                    "description": "Software license",
                    "vendor_id": vendor_acme["id"],
                    "project_id": project_beta["id"],
                    "vendor": vendor_acme,
                    "project": project_beta,
                    "status": "pending",
                    "created_at": "2024-01-20T14:30:00Z",
                },
                {
                    "id": str(uuid4()),
                    "client_id": default_client_id,
                    "amount": 500.00,
                    "date": "2024-01-25",
                    "description": "Hardware",
                    "vendor_id": vendor_tech["id"],
                    "project_id": project_alpha["id"],
                    "vendor": vendor_tech,
                    "project": project_alpha,
                    "status": "paid",
                    "created_at": "2024-01-25T11:00:00Z",
                },
                # Client 2 bill (should not be visible to client 1)
                {
                    "id": str(uuid4()),
                    "client_id": client_2_id,
                    "amount": 9999.99,
                    "date": "2024-01-30",
                    "description": "Client 2 bill",
                    "vendor_id": vendor_client2["id"],
                    "project_id": project_client2["id"],
                    "vendor": vendor_client2,
                    "project": project_client2,
                    "status": "pending",
                    "created_at": "2024-01-30T12:00:00Z",
                },
            ],
            ExportEntity.INVOICE: [
                {
                    "id": str(uuid4()),
                    "client_id": default_client_id,
                    "amount": 5000.00,
                    "date": "2024-01-10",
                    "due_date": "2024-02-10",
                    "description": "Consulting services",
                    "vendor_id": vendor_tech["id"],
                    "project_id": project_alpha["id"],
                    "vendor": vendor_tech,
                    "project": project_alpha,
                    "status": "sent",
                    "created_at": "2024-01-10T09:00:00Z",
                },
                # Client 2 invoice (should not be visible to client 1)
                {
                    "id": str(uuid4()),
                    "client_id": client_2_id,
                    "amount": 8888.88,
                    "date": "2024-01-12",
                    "due_date": "2024-02-12",
                    "description": "Client 2 invoice",
                    "vendor_id": vendor_client2["id"],
                    "project_id": project_client2["id"],
                    "vendor": vendor_client2,
                    "project": project_client2,
                    "status": "sent",
                    "created_at": "2024-01-12T10:00:00Z",
                },
            ],
            ExportEntity.VENDOR: [vendor_acme, vendor_tech, vendor_client2],
            ExportEntity.PROJECT: [project_alpha, project_beta, project_client2],
        }

        # Save to file if configured
        if self.data_file:
            self._save_data()

    def _save_data(self):
        """Save current data to file."""
        if not self.data_file:
            return
        try:
            # Convert ExportEntity enum keys to strings for JSON serialization
            data_to_save = {k.value: v for k, v in self._sample_data.items()}
            Path(self.data_file).parent.mkdir(parents=True, exist_ok=True)
            with open(self.data_file, "w") as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved mock data to {self.data_file}")
        except Exception as e:
            logger.warning(f"Failed to save data to {self.data_file}: {e}")

    async def fetch_data(
        self,
        entity: ExportEntity,
        client_id: UUID,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch mock data for an entity, filtered by client_id for security.

        Only returns records that belong to the specified client_id.
        This ensures multi-tenant data isolation.
        """
        # Log external service call input
        filter_summary = "present" if filters else "none"
        logger.info(
            f"SaaS API fetch_data request: entity={entity.value}, client_id={client_id}, filters={filter_summary}"
        )

        all_data: list[dict[str, Any]] = self._sample_data.get(entity, [])

        # SECURITY: Filter by client_id to ensure data isolation
        # Only return records owned by the requesting client
        client_id_str = str(client_id)
        data = [record for record in all_data if record.get("client_id") == client_id_str]

        # Apply additional filters if provided (simplified mock filtering)
        if filters:
            # In real implementation, would apply actual filtering
            pass

        # Log external service call output
        logger.info(
            f"SaaS API fetch_data response: entity={entity.value}, client_id={client_id}, "
            f"record_count={len(data)} (filtered from {len(all_data)} total)"
        )

        return data

    async def import_data(
        self, config: ImportConfig, client_id: UUID, data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Mock import operation that actually stores data with detailed error reporting.

        SECURITY: All imported records are automatically associated with the specified client_id.
        This ensures data ownership and prevents cross-client data leakage.

        For BILL and INVOICE entities:
        - If record has 'id' and it exists (and belongs to the same client), updates the record
        - Otherwise, creates a new record with the client_id

        Returns count of imported/updated records and any errors with row information.
        """
        # Log external service call input
        logger.info(
            f"SaaS API import_data request: entity={config.entity.value}, client_id={client_id}, "
            f"record_count={len(data)}, source={config.source}"
        )

        entity = config.entity
        client_id_str = str(client_id)
        imported_count = 0
        updated_count = 0
        failed_count = 0
        errors: list[dict[str, Any]] = []

        # Get current data for this entity (filtered by client_id for security)
        all_data = self._sample_data.get(entity, [])
        current_data = [record for record in all_data if record.get("client_id") == client_id_str]

        # Track row number for error reporting (1-based for user-friendly reporting)
        for row_num, record in enumerate(data, start=1):
            try:
                # Validate required fields
                required_fields = (
                    ["amount", "date"]
                    if entity in [ExportEntity.BILL, ExportEntity.INVOICE]
                    else []
                )
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
                        continue

                # SECURITY: Ensure all records have the correct client_id
                # This prevents clients from importing data with a different client_id
                record["client_id"] = client_id_str

                # If record has an ID, try to find and update existing record
                record_id = record.get("id")
                if record_id:
                    # Find existing record by ID (only within this client's data)
                    existing_index = None
                    for i, existing in enumerate(current_data):
                        if existing.get("id") == record_id:
                            # SECURITY: Verify the existing record belongs to the same client
                            if existing.get("client_id") != client_id_str:
                                errors.append(
                                    {
                                        "row": row_num,
                                        "field": "id",
                                        "message": f"Record with id '{record_id}' belongs to a different client and cannot be updated",
                                    }
                                )
                                failed_count += 1
                                continue
                            existing_index = i
                            break

                    if existing_index is not None:
                        # Update existing record (merge with existing data, preserve client_id)
                        current_data[existing_index].update(record)
                        # Ensure client_id is not overwritten
                        current_data[existing_index]["client_id"] = client_id_str
                        updated_count += 1
                        logger.debug(
                            f"Updated {entity.value} record {record_id} for client {client_id}"
                        )
                    else:
                        # Create new record with provided ID
                        if "id" not in record:
                            record["id"] = str(uuid4())
                        current_data.append(record)
                        imported_count += 1
                        logger.debug(
                            f"Created {entity.value} record {record.get('id')} for client {client_id}"
                        )
                else:
                    # Create new record with generated ID
                    record["id"] = str(uuid4())
                    if "created_at" not in record:
                        from datetime import UTC, datetime

                        record["created_at"] = datetime.now(UTC).isoformat() + "Z"
                    current_data.append(record)
                    imported_count += 1
                    logger.debug(
                        f"Created new {entity.value} record {record['id']} for client {client_id}"
                    )

            except Exception as e:
                error_msg = f"Failed to import record: {str(e)}"
                logger.error(f"Row {row_num}: {error_msg}", exc_info=True)
                errors.append({"row": row_num, "message": error_msg})
                failed_count += 1

        # Update the sample data
        # Merge client's data back with other clients' data
        other_clients_data = [
            record for record in all_data if record.get("client_id") != client_id_str
        ]
        self._sample_data[entity] = current_data + other_clients_data

        # Save to file if configured
        if self.data_file:
            self._save_data()

        result: dict[str, Any] = {
            "imported_count": imported_count,
            "updated_count": updated_count,
            "failed_count": failed_count,
            "entity": config.entity.value,
        }

        # Include errors if any
        if errors:
            result["errors"] = errors

        # Log external service call output
        logger.info(
            f"SaaS API import_data response: entity={config.entity.value}, "
            f"imported={imported_count}, updated={updated_count}, failed={failed_count}, "
            f"error_count={len(errors)}"
        )

        return result
