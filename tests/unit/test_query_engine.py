"""Unit tests for query engine with mocked dependencies."""

from unittest.mock import MagicMock
from uuid import UUID

import pytest

from app.domain.entities import (
    ExportConfig,
    ExportEntity,
    ExportFilter,
    ExportFilterGroup,
    ExportFilterOperator,
    LogicalOperator,
)
from app.infrastructure.query.engine import ExportQueryEngine
from app.infrastructure.saas.client import MockSaaSApiClient


@pytest.fixture
def mock_db():
    """Create a mocked database."""
    return MagicMock()


@pytest.fixture
def mock_saas_client():
    """Create a mocked SaaS client."""
    client = MockSaaSApiClient()
    return client


@pytest.fixture
def query_engine(mock_db, mock_saas_client):
    """Create a query engine with mocked dependencies."""
    return ExportQueryEngine(mock_db, mock_saas_client)


@pytest.mark.asyncio
async def test_execute_export_query_basic(query_engine: ExportQueryEngine):
    """Test basic export query execution with deep validation."""
    config = ExportConfig(
        entity=ExportEntity.BILL,
        fields=["id", "amount", "date"],
        limit=10,
        offset=0,
    )
    client_id = UUID("00000000-0000-0000-0000-000000000000")
    result = await query_engine.execute_export_query(config, client_id=client_id)

    # Structure validation
    assert result is not None
    assert "entity" in result
    assert "count" in result
    assert "records" in result
    assert result["entity"] == "bill"

    # Deep validation: Verify all records have ONLY the requested fields
    requested_fields = {"id", "amount", "date"}
    for record in result["records"]:
        record_fields = set(record.keys())
        assert record_fields == requested_fields, (
            f"Field selection failed: Record has fields {record_fields}, expected {requested_fields}"
        )

        # Verify fields have appropriate types/values
        assert "id" in record
        assert "amount" in record
        assert "date" in record
        # Amount should be numeric
        assert isinstance(record["amount"], (int, float)), (
            f"Amount should be numeric, got {type(record['amount'])}"
        )

    # Verify pagination is correct
    assert len(result["records"]) <= config.limit, (
        f"Returned {len(result['records'])} records, but limit is {config.limit}"
    )
    assert result["count"] >= len(result["records"]), (
        f"Total count {result['count']} should be >= returned records {len(result['records'])}"
    )
    assert result["limit"] == config.limit
    assert result["offset"] == config.offset


@pytest.mark.asyncio
async def test_execute_export_query_with_filters(query_engine: ExportQueryEngine):
    """Test export query with filters - deep validation."""
    filter_item = ExportFilter(
        field="amount",
        operator=ExportFilterOperator.GT,
        value=1000,
    )
    filter_group = ExportFilterGroup(
        operator=LogicalOperator.AND,
        filters=[filter_item],
    )
    config = ExportConfig(
        entity=ExportEntity.BILL,
        fields=["id", "amount"],
        filters=filter_group,
        limit=10,
    )
    client_id = UUID("00000000-0000-0000-0000-000000000000")
    result = await query_engine.execute_export_query(config, client_id=client_id)
    assert result is not None
    assert result["count"] >= 0

    # Deep validation: Verify ALL records actually match the filter
    for record in result["records"]:
        assert record["amount"] > 1000, (
            f"Filter failed: Record {record} has amount {record['amount']} which is not > 1000"
        )


@pytest.mark.asyncio
async def test_execute_export_query_with_sort(query_engine: ExportQueryEngine):
    """Test export query with sorting - deep validation."""
    config = ExportConfig(
        entity=ExportEntity.BILL,
        fields=["id", "amount", "date"],
        sort=[{"field": "date", "direction": "desc"}],
        limit=10,
    )
    client_id = UUID("00000000-0000-0000-0000-000000000000")
    result = await query_engine.execute_export_query(config, client_id=client_id)
    assert result is not None
    assert len(result["records"]) <= 10

    # Deep validation: Verify records are actually sorted in descending order
    if len(result["records"]) > 1:
        dates = [record["date"] for record in result["records"]]
        for i in range(len(dates) - 1):
            assert dates[i] >= dates[i + 1], (
                f"Sort failed: dates not in descending order: {dates[i]} < {dates[i + 1]}"
            )


@pytest.mark.asyncio
async def test_execute_export_query_pagination(query_engine: ExportQueryEngine):
    """Test export query with pagination - deep validation."""
    config = ExportConfig(
        entity=ExportEntity.BILL,
        fields=["id", "amount"],
        sort=[{"field": "amount", "direction": "asc"}],  # Sort for predictable pagination
        limit=2,
        offset=0,
    )
    client_id = UUID("00000000-0000-0000-0000-000000000000")
    result1 = await query_engine.execute_export_query(config, client_id=client_id)

    config.offset = 2
    result2 = await query_engine.execute_export_query(config, client_id=client_id)

    assert result1 is not None
    assert result2 is not None
    assert len(result1["records"]) <= 2
    assert len(result2["records"]) <= 2

    # Deep validation: Verify pages don't overlap and total count is consistent
    assert result1["count"] == result2["count"], "Total count should be same for both pages"

    page1_ids = {record["id"] for record in result1["records"]}
    page2_ids = {record["id"] for record in result2["records"]}
    assert page1_ids.isdisjoint(page2_ids), (
        f"Pagination failed: Pages overlap. Page 1: {page1_ids}, Page 2: {page2_ids}"
    )


@pytest.mark.asyncio
async def test_apply_filters_complex(query_engine: ExportQueryEngine):
    """Test complex filter application - deep validation."""
    from app.domain.entities import (
        ExportFilter,
        ExportFilterGroup,
        ExportFilterOperator,
        LogicalOperator,
    )

    # Create complex filter: (amount > 1000) AND (vendor.name contains "Acme")
    filter1 = ExportFilter(
        field="amount",
        operator=ExportFilterOperator.GT,
        value=1000,
    )
    filter2 = ExportFilter(
        field="vendor.name",
        operator=ExportFilterOperator.CONTAINS,
        value="Acme",
    )
    filter_group = ExportFilterGroup(
        operator=LogicalOperator.AND,
        filters=[filter1, filter2],
    )

    config = ExportConfig(
        entity=ExportEntity.BILL,
        fields=["id", "amount", "vendor.name"],
        filters=filter_group,
        limit=10,
    )

    client_id = UUID("00000000-0000-0000-0000-000000000000")
    result = await query_engine.execute_export_query(config, client_id=client_id)
    assert result is not None
    assert result["count"] >= 0

    # Deep validation: Verify ALL records match BOTH filter conditions
    for record in result["records"]:
        assert record["amount"] > 1000, (
            f"Filter failed: Record {record} has amount {record['amount']} which is not > 1000"
        )
        vendor_name = record.get("vendor.name", "")
        assert "acme" in vendor_name.lower(), (
            f"Filter failed: Record {record} vendor.name '{vendor_name}' does not contain 'Acme'"
        )


@pytest.mark.asyncio
async def test_apply_sorting_multiple_fields(query_engine: ExportQueryEngine):
    """Test sorting with multiple fields - deep validation."""
    config = ExportConfig(
        entity=ExportEntity.BILL,
        fields=["id", "amount", "date"],
        sort=[
            {"field": "date", "direction": "desc"},
            {"field": "amount", "direction": "asc"},
        ],
        limit=10,
    )

    client_id = UUID("00000000-0000-0000-0000-000000000000")
    result = await query_engine.execute_export_query(config, client_id=client_id)
    assert result is not None
    assert len(result["records"]) <= 10

    # Deep validation: Verify multi-field sorting is correct
    if len(result["records"]) > 1:
        records = result["records"]
        for i in range(len(records) - 1):
            curr_date = records[i]["date"]
            next_date = records[i + 1]["date"]
            curr_amount = records[i]["amount"]
            next_amount = records[i + 1]["amount"]

            # Compare dates as strings (ISO format YYYY-MM-DD sorts correctly as strings)
            # If dates are equal, amounts should be ascending
            if curr_date == next_date:
                assert curr_amount <= next_amount, (
                    f"Multi-sort failed: Same date {curr_date} but amounts not ascending: {curr_amount} > {next_amount}"
                )
            else:
                # Dates should be descending (as strings, "2024-01-20" > "2024-01-15")
                # Note: String comparison works for ISO dates: "2024-01-20" > "2024-01-15"
                date_descending = curr_date >= next_date
                assert date_descending, (
                    f"Multi-sort failed: Dates not descending: {curr_date} < {next_date} at position {i}. "
                    f"Record {i}: date={curr_date}, amount={curr_amount}; "
                    f"Record {i + 1}: date={next_date}, amount={next_amount}"
                )


@pytest.mark.asyncio
async def test_select_fields_nested(query_engine: ExportQueryEngine):
    """Test field selection with nested fields - deep validation."""
    config = ExportConfig(
        entity=ExportEntity.BILL,
        fields=["id", "amount", "vendor.name", "project.code"],
        limit=10,
    )

    client_id = UUID("00000000-0000-0000-0000-000000000000")
    result = await query_engine.execute_export_query(config, client_id=client_id)
    assert result is not None

    # Deep validation: Verify ALL records have ONLY the requested fields
    requested_fields = {"id", "amount", "vendor.name", "project.code"}
    for record in result["records"]:
        record_fields = set(record.keys())
        assert record_fields == requested_fields, (
            f"Field selection failed: Record {record} has fields {record_fields}, expected {requested_fields}"
        )

        # Verify nested fields are present and have values
        assert "vendor.name" in record, f"Record {record} missing vendor.name"
        assert "project.code" in record, f"Record {record} missing project.code"
        assert record["vendor.name"] is not None, f"Record {record} has None for vendor.name"
        assert record["project.code"] is not None, f"Record {record} has None for project.code"
