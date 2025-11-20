"""Deep validation tests for query engine - comprehensive filter, sort, and pagination checks."""

from unittest.mock import MagicMock

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
    """Create a SaaS client with known test data."""
    client = MockSaaSApiClient()
    # Ensure we have predictable test data
    # The MockSaaSApiClient already has sample bills with known amounts
    return client


@pytest.fixture
def query_engine(mock_db, mock_saas_client):
    """Create a query engine with mocked dependencies."""
    return ExportQueryEngine(mock_db, mock_saas_client)


@pytest.mark.asyncio
async def test_filter_operators_comprehensive(query_engine):
    """Test all filter operators with deep validation."""
    test_cases = [
        (ExportFilterOperator.EQ, 1000.50, lambda val, expected: val == expected),
        (ExportFilterOperator.NE, 1000.50, lambda val, expected: val != expected),
        (ExportFilterOperator.GT, 1000, lambda val, expected: val > expected),
        (ExportFilterOperator.GTE, 1000.50, lambda val, expected: val >= expected),
        (ExportFilterOperator.LT, 2500, lambda val, expected: val < expected),
        (ExportFilterOperator.LTE, 2500.00, lambda val, expected: val <= expected),
    ]

    for operator, value, check_func in test_cases:
        filter_item = ExportFilter(
            field="amount",
            operator=operator,
            value=value,
        )
        filter_group = ExportFilterGroup(
            operator=LogicalOperator.AND,
            filters=[filter_item],
        )

        config = ExportConfig(
            entity=ExportEntity.BILL,
            fields=["id", "amount"],
            filters=filter_group,
            limit=100,
        )

        result = await query_engine.execute_export_query(config)

        # Deep validation: Verify ALL records match the filter
        for record in result["records"]:
            assert check_func(record["amount"], value), (
                f"Filter {operator.value} failed: Record {record} amount {record['amount']} does not satisfy {operator.value} {value}"
            )


@pytest.mark.asyncio
async def test_filter_in_operator(query_engine):
    """Test IN operator with deep validation."""
    filter_item = ExportFilter(
        field="amount",
        operator=ExportFilterOperator.IN,
        value=[1000.50, 2500.00],
    )
    filter_group = ExportFilterGroup(
        operator=LogicalOperator.AND,
        filters=[filter_item],
    )

    config = ExportConfig(
        entity=ExportEntity.BILL,
        fields=["id", "amount"],
        filters=filter_group,
        limit=100,
    )

    result = await query_engine.execute_export_query(config)

    # Deep validation: Verify ALL records have amounts in the specified list
    for record in result["records"]:
        assert record["amount"] in [1000.50, 2500.00], (
            f"IN filter failed: Record {record} amount {record['amount']} not in [1000.50, 2500.00]"
        )


@pytest.mark.asyncio
async def test_filter_between_operator(query_engine):
    """Test BETWEEN operator with deep validation."""
    filter_item = ExportFilter(
        field="amount",
        operator=ExportFilterOperator.BETWEEN,
        value=[500, 2000],
    )
    filter_group = ExportFilterGroup(
        operator=LogicalOperator.AND,
        filters=[filter_item],
    )

    config = ExportConfig(
        entity=ExportEntity.BILL,
        fields=["id", "amount"],
        filters=filter_group,
        limit=100,
    )

    result = await query_engine.execute_export_query(config)

    # Deep validation: Verify ALL records have amounts between 500 and 2000
    for record in result["records"]:
        assert 500 <= record["amount"] <= 2000, (
            f"BETWEEN filter failed: Record {record} amount {record['amount']} not between 500 and 2000"
        )


@pytest.mark.asyncio
async def test_filter_contains_operator(query_engine):
    """Test CONTAINS operator with deep validation."""
    filter_item = ExportFilter(
        field="description",
        operator=ExportFilterOperator.CONTAINS,
        value="Office",
    )
    filter_group = ExportFilterGroup(
        operator=LogicalOperator.AND,
        filters=[filter_item],
    )

    config = ExportConfig(
        entity=ExportEntity.BILL,
        fields=["id", "description"],
        filters=filter_group,
        limit=100,
    )

    result = await query_engine.execute_export_query(config)

    # Deep validation: Verify ALL records have descriptions containing "Office" (case-insensitive)
    for record in result["records"]:
        description = str(record.get("description", "")).lower()
        assert "office" in description, (
            f"CONTAINS filter failed: Record {record} description '{record.get('description')}' does not contain 'Office'"
        )


@pytest.mark.asyncio
async def test_filter_or_operator(query_engine):
    """Test OR operator with deep validation."""
    filter1 = ExportFilter(
        field="amount",
        operator=ExportFilterOperator.GT,
        value=2000,
    )
    filter2 = ExportFilter(
        field="status",
        operator=ExportFilterOperator.EQ,
        value="pending",
    )
    filter_group = ExportFilterGroup(
        operator=LogicalOperator.OR,
        filters=[filter1, filter2],
    )

    config = ExportConfig(
        entity=ExportEntity.BILL,
        fields=["id", "amount", "status"],
        filters=filter_group,
        limit=100,
    )

    result = await query_engine.execute_export_query(config)

    # Deep validation: Verify ALL records match at least ONE condition
    for record in result["records"]:
        matches_filter1 = record["amount"] > 2000
        matches_filter2 = record.get("status") == "pending"
        assert matches_filter1 or matches_filter2, (
            f"OR filter failed: Record {record} matches neither condition (amount > 2000 OR status == 'pending')"
        )


@pytest.mark.asyncio
async def test_sort_ascending(query_engine):
    """Test ascending sort with deep validation."""
    config = ExportConfig(
        entity=ExportEntity.BILL,
        fields=["id", "amount"],
        sort=[{"field": "amount", "direction": "asc"}],
        limit=100,
    )

    result = await query_engine.execute_export_query(config)

    # Deep validation: Verify records are in ascending order
    if len(result["records"]) > 1:
        amounts = [record["amount"] for record in result["records"]]
        for i in range(len(amounts) - 1):
            assert amounts[i] <= amounts[i + 1], (
                f"Sort ASC failed: amounts not in ascending order: {amounts[i]} > {amounts[i + 1]} at position {i}"
            )


@pytest.mark.asyncio
async def test_pagination_consistency(query_engine):
    """Test pagination consistency with deep validation."""
    # Get all records first
    config_all = ExportConfig(
        entity=ExportEntity.BILL,
        fields=["id", "amount"],
        sort=[{"field": "amount", "direction": "asc"}],  # Sort for consistency
        limit=1000,
        offset=0,
    )
    result_all = await query_engine.execute_export_query(config_all)
    all_ids = {record["id"] for record in result_all["records"]}
    total_count = result_all["count"]

    # Get paginated results
    page_size = 2
    all_paginated_ids = set()

    for offset in range(0, total_count, page_size):
        config_page = ExportConfig(
            entity=ExportEntity.BILL,
            fields=["id", "amount"],
            sort=[{"field": "amount", "direction": "asc"}],
            limit=page_size,
            offset=offset,
        )
        result_page = await query_engine.execute_export_query(config_page)
        page_ids = {record["id"] for record in result_page["records"]}

        # Deep validation: Verify no duplicates across pages
        assert all_paginated_ids.isdisjoint(page_ids), (
            f"Pagination failed: Page at offset {offset} has duplicate IDs: {page_ids.intersection(all_paginated_ids)}"
        )

        all_paginated_ids.update(page_ids)

        # Deep validation: Verify page size is correct (except last page)
        if offset + page_size < total_count:
            assert len(result_page["records"]) == page_size, (
                f"Pagination failed: Page at offset {offset} has {len(result_page['records'])} records, expected {page_size}"
            )

    # Deep validation: Verify all records are accounted for
    assert all_paginated_ids == all_ids, (
        f"Pagination failed: Paginated IDs {all_paginated_ids} don't match all IDs {all_ids}"
    )


@pytest.mark.asyncio
async def test_field_selection_excludes_unrequested(query_engine):
    """Test that only requested fields are returned."""
    config = ExportConfig(
        entity=ExportEntity.BILL,
        fields=["id", "amount"],  # Only request id and amount
        limit=10,
    )

    result = await query_engine.execute_export_query(config)

    # Deep validation: Verify records have ONLY requested fields
    requested_fields = {"id", "amount"}
    for record in result["records"]:
        record_fields = set(record.keys())
        assert record_fields == requested_fields, (
            f"Field selection failed: Record {record} has fields {record_fields}, expected only {requested_fields}"
        )

        # Verify fields are not None/empty
        assert record["id"] is not None
        assert record["amount"] is not None


@pytest.mark.asyncio
async def test_nested_field_filtering(query_engine):
    """Test filtering on nested fields with deep validation."""
    filter_item = ExportFilter(
        field="vendor.name",
        operator=ExportFilterOperator.CONTAINS,
        value="Acme",
    )
    filter_group = ExportFilterGroup(
        operator=LogicalOperator.AND,
        filters=[filter_item],
    )

    config = ExportConfig(
        entity=ExportEntity.BILL,
        fields=["id", "amount", "vendor.name"],
        filters=filter_group,
        limit=100,
    )

    result = await query_engine.execute_export_query(config)

    # Deep validation: Verify ALL records have vendor.name containing "Acme"
    for record in result["records"]:
        vendor_name = record.get("vendor.name", "")
        assert "acme" in str(vendor_name).lower(), (
            f"Nested filter failed: Record {record} vendor.name '{vendor_name}' does not contain 'Acme'"
        )

        # Verify nested field is actually returned
        assert "vendor.name" in record, (
            f"Record {record} missing requested nested field 'vendor.name'"
        )
