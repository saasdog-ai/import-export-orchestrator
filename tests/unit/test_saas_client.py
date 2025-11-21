"""Unit tests for SaaS client."""

import json
from uuid import UUID, uuid4

import pytest

from app.domain.entities import ExportEntity
from app.infrastructure.saas.client import MockSaaSApiClient


class TestMockSaaSApiClient:
    """Test cases for MockSaaSApiClient."""

    def test_init_without_data_file(self):
        """Test client initialization without data file."""
        client = MockSaaSApiClient()

        assert ExportEntity.BILL in client._sample_data
        assert ExportEntity.INVOICE in client._sample_data
        assert ExportEntity.VENDOR in client._sample_data
        assert ExportEntity.PROJECT in client._sample_data
        assert len(client._sample_data[ExportEntity.BILL]) > 0

    def test_init_with_data_file(self, tmp_path):
        """Test client initialization with data file."""
        data_file = tmp_path / "test_data.json"
        test_data = {"bill": [{"id": "test-1", "amount": 100.00, "date": "2024-01-01"}]}
        with open(data_file, "w") as f:
            json.dump(test_data, f)

        client = MockSaaSApiClient(data_file=str(data_file))

        assert ExportEntity.BILL in client._sample_data
        assert len(client._sample_data[ExportEntity.BILL]) == 1
        assert client._sample_data[ExportEntity.BILL][0]["id"] == "test-1"

    def test_init_with_nonexistent_data_file(self):
        """Test client initialization with non-existent data file (should use defaults)."""
        client = MockSaaSApiClient(data_file="/nonexistent/file.json")

        # Should fall back to default data
        assert ExportEntity.BILL in client._sample_data
        assert len(client._sample_data[ExportEntity.BILL]) > 0

    @pytest.mark.asyncio
    async def test_fetch_data_basic(self):
        """Test basic data fetching with client_id filtering."""
        client = MockSaaSApiClient()
        client_id = UUID("00000000-0000-0000-0000-000000000000")

        data = await client.fetch_data(ExportEntity.BILL, client_id=client_id)

        assert isinstance(data, list)
        assert len(data) > 0
        assert "id" in data[0]
        assert "amount" in data[0]
        # Verify all records belong to the requested client
        for record in data:
            assert record.get("client_id") == str(client_id)

    @pytest.mark.asyncio
    async def test_fetch_data_with_filters(self):
        """Test data fetching with filters and client_id."""
        client = MockSaaSApiClient()
        client_id = UUID("00000000-0000-0000-0000-000000000000")

        # Add a bill with specific amount for filtering
        test_bill = {
            "id": str(uuid4()),
            "client_id": str(client_id),
            "amount": 9999.99,
            "date": "2024-01-01",
            "description": "Test bill",
            "status": "paid",
        }
        client._sample_data[ExportEntity.BILL].append(test_bill)

        data = await client.fetch_data(
            ExportEntity.BILL, client_id=client_id, filters={"amount": 9999.99}
        )

        # Mock client doesn't actually filter, but should return data filtered by client_id
        assert isinstance(data, list)
        # Verify all records belong to the requested client
        for record in data:
            assert record.get("client_id") == str(client_id)

    @pytest.mark.asyncio
    async def test_import_data_create_new(self):
        """Test importing new records with client_id."""
        client = MockSaaSApiClient()
        from app.domain.entities import ImportConfig

        client_id = UUID("00000000-0000-0000-0000-000000000000")
        # Count only records for this client
        initial_count = len(
            [
                r
                for r in client._sample_data[ExportEntity.BILL]
                if r.get("client_id") == str(client_id)
            ]
        )

        import_data = [{"amount": "500.00", "date": "2024-02-01", "description": "New bill"}]

        config = ImportConfig(
            source="test",
            entity=ExportEntity.BILL,
        )

        result = await client.import_data(config, client_id=client_id, data=import_data)

        assert result["imported_count"] == 1
        assert result["updated_count"] == 0
        assert result["failed_count"] == 0
        # Verify the new record has the correct client_id
        new_records = [
            r
            for r in client._sample_data[ExportEntity.BILL]
            if r.get("client_id") == str(client_id)
        ]
        assert len(new_records) == initial_count + 1
        # Verify the imported record has client_id
        imported_record = new_records[-1]
        assert imported_record.get("client_id") == str(client_id)

    @pytest.mark.asyncio
    async def test_import_data_update_existing(self):
        """Test importing with existing ID (update) and client_id."""
        client = MockSaaSApiClient()
        from app.domain.entities import ImportConfig

        client_id = UUID("00000000-0000-0000-0000-000000000000")
        # Get an existing bill ID for this client
        existing_bill = next(
            b
            for b in client._sample_data[ExportEntity.BILL]
            if b.get("client_id") == str(client_id)
        )
        existing_id = existing_bill["id"]
        initial_count = len(client._sample_data[ExportEntity.BILL])

        import_data = [
            {
                "id": existing_id,
                "amount": "9999.99",
                "date": "2024-02-01",
                "description": "Updated bill",
            }
        ]

        config = ImportConfig(
            source="test",
            entity=ExportEntity.BILL,
        )

        result = await client.import_data(config, client_id=client_id, data=import_data)

        assert result["updated_count"] == 1
        assert result["imported_count"] == 0
        assert result["failed_count"] == 0
        assert len(client._sample_data[ExportEntity.BILL]) == initial_count
        # Verify the bill was updated and still has correct client_id
        updated_bill = next(
            b for b in client._sample_data[ExportEntity.BILL] if b["id"] == existing_id
        )
        assert updated_bill["amount"] == "9999.99"
        assert updated_bill.get("client_id") == str(client_id)

    @pytest.mark.asyncio
    async def test_import_data_with_errors(self):
        """Test importing data with validation errors and client_id."""
        client = MockSaaSApiClient()
        from app.domain.entities import ImportConfig

        client_id = UUID("00000000-0000-0000-0000-000000000000")
        # Import data with missing required fields
        import_data = [
            {"description": "Missing amount and date"}  # Missing required fields
        ]

        config = ImportConfig(
            source="test",
            entity=ExportEntity.BILL,
        )

        result = await client.import_data(config, client_id=client_id, data=import_data)

        # Should have errors for missing required fields
        assert result["failed_count"] > 0
        assert "errors" in result
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_import_data_saves_to_file(self, tmp_path):
        """Test that import data is saved to file when data_file is set."""
        data_file = tmp_path / "test_data.json"
        client = MockSaaSApiClient(data_file=str(data_file))
        from app.domain.entities import ImportConfig

        client_id = UUID("00000000-0000-0000-0000-000000000000")
        import_data = [{"amount": "500.00", "date": "2024-02-01", "description": "New bill"}]

        config = ImportConfig(
            source="test",
            entity=ExportEntity.BILL,
        )

        await client.import_data(config, client_id=client_id, data=import_data)

        # Verify file was created/updated
        assert data_file.exists()
        with open(data_file) as f:
            saved_data = json.load(f)
            assert "bill" in saved_data

    def test_save_data(self, tmp_path):
        """Test saving data to file."""
        data_file = tmp_path / "test_data.json"
        client = MockSaaSApiClient(data_file=str(data_file))

        # Modify data (add client_id for consistency)
        client._sample_data[ExportEntity.BILL].append(
            {
                "id": "test-id",
                "client_id": "00000000-0000-0000-0000-000000000000",
                "amount": 100.00,
                "date": "2024-01-01",
            }
        )

        client._save_data()

        # Verify file was saved
        assert data_file.exists()
        with open(data_file) as f:
            saved_data = json.load(f)
            assert "bill" in saved_data
