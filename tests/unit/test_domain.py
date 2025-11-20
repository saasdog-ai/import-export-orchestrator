"""Unit tests for domain entities."""

from uuid import uuid4

import pytest

from app.domain.entities import (
    ExportConfig,
    ExportEntity,
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
        fields=["id", "amount", "date"],
        limit=100,
        offset=0,
    )
    assert config.entity == ExportEntity.BILL
    assert config.fields == ["id", "amount", "date"]
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
        fields=["id", "amount"],
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

