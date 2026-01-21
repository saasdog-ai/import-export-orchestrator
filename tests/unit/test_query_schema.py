"""Unit tests for query schema validation."""

from app.domain.entities import ExportEntity
from app.infrastructure.query.schema import validate_field_path


def test_validate_field_path_bill():
    """Test field path validation for BILL entity."""
    # Valid fields - core
    assert validate_field_path(ExportEntity.BILL, "id") is True
    assert validate_field_path(ExportEntity.BILL, "external_id") is True
    assert validate_field_path(ExportEntity.BILL, "amount") is True
    assert validate_field_path(ExportEntity.BILL, "date") is True
    assert validate_field_path(ExportEntity.BILL, "due_date") is True
    assert validate_field_path(ExportEntity.BILL, "description") is True
    assert validate_field_path(ExportEntity.BILL, "currency") is True
    assert validate_field_path(ExportEntity.BILL, "status") is True
    assert validate_field_path(ExportEntity.BILL, "vendor_id") is True
    assert validate_field_path(ExportEntity.BILL, "project_id") is True

    # Valid fields - timestamps
    assert validate_field_path(ExportEntity.BILL, "created_at") is True
    assert validate_field_path(ExportEntity.BILL, "updated_at") is True

    # Valid nested fields
    assert validate_field_path(ExportEntity.BILL, "vendor.name") is True
    assert validate_field_path(ExportEntity.BILL, "project.code") is True

    # Invalid fields
    assert validate_field_path(ExportEntity.BILL, "invalid_field") is False
    assert validate_field_path(ExportEntity.BILL, "vendor.invalid") is False


def test_validate_field_path_invoice():
    """Test field path validation for INVOICE entity."""
    # Valid fields - core
    assert validate_field_path(ExportEntity.INVOICE, "id") is True
    assert validate_field_path(ExportEntity.INVOICE, "external_id") is True
    assert validate_field_path(ExportEntity.INVOICE, "amount") is True
    assert validate_field_path(ExportEntity.INVOICE, "date") is True
    assert validate_field_path(ExportEntity.INVOICE, "due_date") is True
    assert validate_field_path(ExportEntity.INVOICE, "description") is True
    assert validate_field_path(ExportEntity.INVOICE, "currency") is True
    assert validate_field_path(ExportEntity.INVOICE, "status") is True
    assert validate_field_path(ExportEntity.INVOICE, "vendor_id") is True
    assert validate_field_path(ExportEntity.INVOICE, "project_id") is True

    # Valid fields - timestamps
    assert validate_field_path(ExportEntity.INVOICE, "created_at") is True
    assert validate_field_path(ExportEntity.INVOICE, "updated_at") is True

    # Valid nested fields
    assert validate_field_path(ExportEntity.INVOICE, "vendor.name") is True
    assert validate_field_path(ExportEntity.INVOICE, "project.code") is True

    # Invalid fields
    assert validate_field_path(ExportEntity.INVOICE, "invalid") is False


def test_validate_field_path_vendor():
    """Test field path validation for VENDOR entity."""
    # Valid fields - core
    assert validate_field_path(ExportEntity.VENDOR, "id") is True
    assert validate_field_path(ExportEntity.VENDOR, "external_id") is True
    assert validate_field_path(ExportEntity.VENDOR, "name") is True
    assert validate_field_path(ExportEntity.VENDOR, "email") is True
    assert validate_field_path(ExportEntity.VENDOR, "phone") is True
    assert validate_field_path(ExportEntity.VENDOR, "address") is True

    # Valid fields - timestamps
    assert validate_field_path(ExportEntity.VENDOR, "created_at") is True
    assert validate_field_path(ExportEntity.VENDOR, "updated_at") is True

    # Invalid fields
    assert validate_field_path(ExportEntity.VENDOR, "amount") is False  # Not a vendor field
    assert validate_field_path(ExportEntity.VENDOR, "vendor.name") is False  # No nested vendor


def test_validate_field_path_project():
    """Test field path validation for PROJECT entity."""
    # Valid fields - core
    assert validate_field_path(ExportEntity.PROJECT, "id") is True
    assert validate_field_path(ExportEntity.PROJECT, "external_id") is True
    assert validate_field_path(ExportEntity.PROJECT, "code") is True
    assert validate_field_path(ExportEntity.PROJECT, "name") is True
    assert validate_field_path(ExportEntity.PROJECT, "description") is True
    assert validate_field_path(ExportEntity.PROJECT, "status") is True

    # Valid fields - timestamps
    assert validate_field_path(ExportEntity.PROJECT, "created_at") is True
    assert validate_field_path(ExportEntity.PROJECT, "updated_at") is True

    # Invalid fields
    assert validate_field_path(ExportEntity.PROJECT, "amount") is False
    assert validate_field_path(ExportEntity.PROJECT, "project.code") is False  # No nested project


def test_validate_field_path_nested():
    """Test nested field path validation."""
    # Valid nested paths
    assert validate_field_path(ExportEntity.BILL, "vendor.name") is True
    assert validate_field_path(ExportEntity.BILL, "vendor.email") is True
    assert validate_field_path(ExportEntity.BILL, "project.code") is True
    assert validate_field_path(ExportEntity.BILL, "project.name") is True

    # Invalid nested paths
    assert validate_field_path(ExportEntity.BILL, "vendor.amount") is False  # amount not in vendor
    assert (
        validate_field_path(ExportEntity.BILL, "project.vendor") is False
    )  # vendor not in project
    assert (
        validate_field_path(ExportEntity.BILL, "vendor.vendor.name") is False
    )  # Too deeply nested
