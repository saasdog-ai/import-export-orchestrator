"""Unit tests for domain entities."""

from uuid import uuid4

import pytest

from app.domain.entities import (
    ExportConfig,
    ExportEntity,
    ExportField,
    ExportFilter,
    ExportFilterGroup,
    ExportFilterOperator,
    ImportConfig,
    JobDefinition,
    JobType,
    LogicalOperator,
)


def test_export_config():
    """Test ExportConfig entity."""
    config = ExportConfig(
        entity=ExportEntity.BILL,
        fields=[
            ExportField(field="id"),
            ExportField(field="amount"),
            ExportField(field="date"),
        ],
        limit=100,
        offset=0,
    )
    assert config.entity == ExportEntity.BILL
    assert config.get_source_fields() == ["id", "amount", "date"]
    assert config.limit == 100
    assert config.offset == 0


def test_export_filter():
    """Test ExportFilter entity."""
    filter_item = ExportFilter(
        field="amount",
        operator=ExportFilterOperator.GT,
        value=1000,
    )
    assert filter_item.field == "amount"
    assert filter_item.operator == ExportFilterOperator.GT
    assert filter_item.value == 1000


def test_export_filter_between():
    """Test ExportFilter with BETWEEN operator."""
    filter_item = ExportFilter(
        field="amount",
        operator=ExportFilterOperator.BETWEEN,
        value=[1000, 5000],
    )
    assert filter_item.value == [1000, 5000]


def test_export_filter_group():
    """Test ExportFilterGroup entity."""
    filter1 = ExportFilter(
        field="amount",
        operator=ExportFilterOperator.GT,
        value=1000,
    )
    filter2 = ExportFilter(
        field="status",
        operator=ExportFilterOperator.EQ,
        value="paid",
    )
    group = ExportFilterGroup(
        operator=LogicalOperator.AND,
        filters=[filter1, filter2],
    )
    assert group.operator == LogicalOperator.AND
    assert len(group.filters) == 2


def test_job_definition_export():
    """Test JobDefinition with export config."""
    config = ExportConfig(
        entity=ExportEntity.BILL,
        fields=[ExportField(field="id"), ExportField(field="amount")],
    )
    job = JobDefinition(
        id=uuid4(),
        client_id=uuid4(),
        name="Test Export Job",
        job_type=JobType.EXPORT,
        export_config=config,
    )
    assert job.job_type == JobType.EXPORT
    assert job.export_config is not None


def test_job_definition_import():
    """Test JobDefinition with import config."""
    config = ImportConfig(
        source="test_source",
        entity=ExportEntity.BILL,
    )
    job = JobDefinition(
        id=uuid4(),
        client_id=uuid4(),
        name="Test Import Job",
        job_type=JobType.IMPORT,
        import_config=config,
    )
    assert job.job_type == JobType.IMPORT
    assert job.import_config is not None


def test_job_definition_missing_config():
    """Test that job definition requires appropriate config."""
    with pytest.raises(ValueError):
        JobDefinition(
            id=uuid4(),
            client_id=uuid4(),
            name="Invalid Job",
            job_type=JobType.EXPORT,
            export_config=None,  # Missing required config
        )


# ============================================================================
# ExportField Aliasing Tests
# ============================================================================


def test_export_field_without_alias():
    """Test ExportField without alias uses field name as output."""
    field = ExportField(field="amount")
    assert field.field == "amount"
    assert field.as_ is None
    assert field.output_name == "amount"


def test_export_field_with_alias():
    """Test ExportField with alias uses alias as output name."""
    field = ExportField(field="amount", **{"as": "Total Amount"})
    assert field.field == "amount"
    assert field.as_ == "Total Amount"
    assert field.output_name == "Total Amount"


def test_export_field_nested_with_alias():
    """Test ExportField for nested field with alias."""
    field = ExportField(field="vendor.name", **{"as": "Vendor Name"})
    assert field.field == "vendor.name"
    assert field.as_ == "Vendor Name"
    assert field.output_name == "Vendor Name"


def test_export_config_get_source_fields():
    """Test ExportConfig.get_source_fields returns source field names."""
    config = ExportConfig(
        entity=ExportEntity.BILL,
        fields=[
            ExportField(field="id"),
            ExportField(field="amount", **{"as": "Total Amount"}),
            ExportField(field="vendor.name", **{"as": "Vendor"}),
        ],
    )
    source_fields = config.get_source_fields()
    assert source_fields == ["id", "amount", "vendor.name"]


def test_export_config_get_field_mappings():
    """Test ExportConfig.get_field_mappings returns source->output mapping."""
    config = ExportConfig(
        entity=ExportEntity.BILL,
        fields=[
            ExportField(field="id"),
            ExportField(field="amount", **{"as": "Total Amount"}),
            ExportField(field="vendor.name", **{"as": "Vendor"}),
        ],
    )
    mappings = config.get_field_mappings()
    assert mappings == {
        "id": "id",  # No alias, uses source field
        "amount": "Total Amount",
        "vendor.name": "Vendor",
    }


def test_export_config_backward_compatible_string_fields():
    """Test ExportConfig accepts string fields for backward compatibility."""
    config = ExportConfig(
        entity=ExportEntity.BILL,
        fields=["id", "amount", "date"],  # type: ignore[arg-type]  # Old format
    )
    # Should be converted to ExportField objects
    assert len(config.fields) == 3
    assert all(isinstance(f, ExportField) for f in config.fields)
    assert config.get_source_fields() == ["id", "amount", "date"]


def test_export_config_mixed_fields():
    """Test ExportConfig with mix of string and object fields."""
    config = ExportConfig(
        entity=ExportEntity.BILL,
        fields=[
            "id",  # type: ignore[list-item]  # Old string format
            {"field": "amount", "as": "Total Amount"},  # New object format
            {"field": "vendor.name"},  # Object without alias
        ],
    )
    assert config.get_source_fields() == ["id", "amount", "vendor.name"]
    mappings = config.get_field_mappings()
    assert mappings["id"] == "id"
    assert mappings["amount"] == "Total Amount"
    assert mappings["vendor.name"] == "vendor.name"
