"""Tests for entity handlers and base SaaS client."""

from app.domain.entities import ExportEntity
from app.infrastructure.saas.base import BaseSaaSApiClient
from app.infrastructure.saas.handlers import (
    BillHandler,
    InvoiceHandler,
    ProjectHandler,
    VendorHandler,
)
from app.infrastructure.saas.utils import parse_date


class TestParseDate:
    """Test the parse_date utility."""

    def test_none_returns_none(self):
        assert parse_date(None) is None

    def test_iso_date_string(self):
        result = parse_date("2024-01-15")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_iso_datetime_string(self):
        result = parse_date("2024-01-15T10:30:00")
        assert result is not None
        assert result.hour == 10
        assert result.minute == 30

    def test_iso_datetime_with_z(self):
        result = parse_date("2024-01-15T10:30:00Z")
        assert result is not None
        assert result.tzinfo is None  # converted to naive UTC

    def test_invalid_string(self):
        assert parse_date("not-a-date") is None

    def test_datetime_passthrough(self):
        from datetime import datetime

        dt = datetime(2024, 1, 15, 10, 30)
        result = parse_date(dt)
        assert result == dt


class TestHandlerRequiredFields:
    """Test that handlers report correct required fields."""

    def test_vendor_required_fields(self):
        assert VendorHandler().get_required_fields() == ["name"]

    def test_project_required_fields(self):
        assert ProjectHandler().get_required_fields() == ["code", "name"]

    def test_bill_required_fields(self):
        assert BillHandler().get_required_fields() == ["amount", "date"]

    def test_invoice_required_fields(self):
        assert InvoiceHandler().get_required_fields() == ["amount", "date"]


class TestHandlerInstantiation:
    """Test that all handlers can be instantiated."""

    def test_all_handlers_instantiate(self):
        handlers = [VendorHandler(), ProjectHandler(), BillHandler(), InvoiceHandler()]
        assert len(handlers) == 4

    def test_handlers_have_required_methods(self):
        """All handlers implement the EntityHandler protocol methods."""
        for handler_cls in [VendorHandler, ProjectHandler, BillHandler, InvoiceHandler]:
            handler = handler_cls()
            assert callable(getattr(handler, "fetch", None))
            assert callable(getattr(handler, "find_existing", None))
            assert callable(getattr(handler, "create", None))
            assert callable(getattr(handler, "update", None))
            assert callable(getattr(handler, "delete", None))
            assert callable(getattr(handler, "get_required_fields", None))


class TestBaseSaaSApiClientRegistration:
    """Test handler registration on BaseSaaSApiClient."""

    def test_register_handler(self):
        """Handlers can be registered on the base client."""
        from unittest.mock import MagicMock

        db = MagicMock()
        client = BaseSaaSApiClient(db)
        handler = VendorHandler()
        client.register_handler(ExportEntity.VENDOR, handler)
        assert client._handlers[ExportEntity.VENDOR] is handler

    def test_all_four_handlers_registered(self):
        """MockSaaSApiClient registers all 4 handlers."""
        from unittest.mock import MagicMock

        from app.infrastructure.saas.client import MockSaaSApiClient

        db = MagicMock()
        client = MockSaaSApiClient(db)
        assert len(client._handlers) == 4
        assert ExportEntity.VENDOR in client._handlers
        assert ExportEntity.PROJECT in client._handlers
        assert ExportEntity.BILL in client._handlers
        assert ExportEntity.INVOICE in client._handlers

    def test_handler_types(self):
        """MockSaaSApiClient registers the correct handler types."""
        from unittest.mock import MagicMock

        from app.infrastructure.saas.client import MockSaaSApiClient

        db = MagicMock()
        client = MockSaaSApiClient(db)
        assert isinstance(client._handlers[ExportEntity.VENDOR], VendorHandler)
        assert isinstance(client._handlers[ExportEntity.PROJECT], ProjectHandler)
        assert isinstance(client._handlers[ExportEntity.BILL], BillHandler)
        assert isinstance(client._handlers[ExportEntity.INVOICE], InvoiceHandler)


class TestClientInterface:
    """Test that the client interface is preserved."""

    def test_interface_has_fetch_data(self):
        from app.infrastructure.saas.client import SaaSApiClientInterface

        assert callable(getattr(SaaSApiClientInterface, "fetch_data", None))

    def test_interface_has_import_data(self):
        from app.infrastructure.saas.client import SaaSApiClientInterface

        assert callable(getattr(SaaSApiClientInterface, "import_data", None))

    def test_mock_client_has_fetch_data(self):
        from unittest.mock import MagicMock

        from app.infrastructure.saas.client import MockSaaSApiClient

        db = MagicMock()
        client = MockSaaSApiClient(db)
        assert callable(getattr(client, "fetch_data", None))

    def test_mock_client_has_import_data(self):
        from unittest.mock import MagicMock

        from app.infrastructure.saas.client import MockSaaSApiClient

        db = MagicMock()
        client = MockSaaSApiClient(db)
        assert callable(getattr(client, "import_data", None))
