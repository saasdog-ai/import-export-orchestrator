"""SaaS API client interface and mock implementation."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.domain.entities import ExportEntity, ImportConfig
from app.infrastructure.db.database import Database
from app.infrastructure.saas.base import BaseSaaSApiClient
from app.infrastructure.saas.handlers import (
    BillHandler,
    InvoiceHandler,
    ProjectHandler,
    VendorHandler,
)

logger = get_logger(__name__)


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


class MockSaaSApiClient(BaseSaaSApiClient, SaaSApiClientInterface):
    """Mock implementation of SaaS API client using database tables for sample data.

    Registers entity handlers for all supported entity types.
    All import/export orchestration is handled by BaseSaaSApiClient.
    """

    def __init__(self, db: Database):
        super().__init__(db)
        self.register_handler(ExportEntity.VENDOR, VendorHandler())
        self.register_handler(ExportEntity.PROJECT, ProjectHandler())
        self.register_handler(ExportEntity.BILL, BillHandler())
        self.register_handler(ExportEntity.INVOICE, InvoiceHandler())
