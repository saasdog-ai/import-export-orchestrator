"""Unit tests for SaaS client."""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open
from uuid import uuid4

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
        test_data = {
            "bill": [
                {"id": "test-1", "amount": 100.00, "date": "2024-01-01"}
            ]
        }
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
        """Test basic data fetching."""
        client = MockSaaSApiClient()
        
        data = await client.fetch_data(ExportEntity.BILL)
        
        assert isinstance(data, list)
        assert len(data) > 0
        assert "id" in data[0]
        assert "amount" in data[0]

    @pytest.mark.asyncio
    async def test_fetch_data_with_filters(self):
        """Test data fetching with filters."""
        client = MockSaaSApiClient()
        
        # Add a bill with specific amount for filtering
        test_bill = {
            "id": str(uuid4()),
            "amount": 9999.99,
            "date": "2024-01-01",
            "description": "Test bill",
            "status": "paid",
        }
        client._sample_data[ExportEntity.BILL].append(test_bill)
        
        data = await client.fetch_data(ExportEntity.BILL, filters={"amount": 9999.99})
        
        # Mock client doesn't actually filter, but should return data
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_import_data_create_new(self):
        """Test importing new records."""
        client = MockSaaSApiClient()
        from app.domain.entities import ImportConfig
        
        initial_count = len(client._sample_data[ExportEntity.BILL])
        
        import_data = [
            {"amount": "500.00", "date": "2024-02-01", "description": "New bill"}
        ]
        
        config = ImportConfig(
            source="test",
            entity=ExportEntity.BILL,
        )
        
        result = await client.import_data(config, import_data)
        
        assert result["imported_count"] == 1
        assert result["updated_count"] == 0
        assert result["failed_count"] == 0
        assert len(client._sample_data[ExportEntity.BILL]) == initial_count + 1

    @pytest.mark.asyncio
    async def test_import_data_update_existing(self):
        """Test importing with existing ID (update)."""
        client = MockSaaSApiClient()
        from app.domain.entities import ImportConfig
        
        # Get an existing bill ID
        existing_bill = client._sample_data[ExportEntity.BILL][0]
        existing_id = existing_bill["id"]
        initial_count = len(client._sample_data[ExportEntity.BILL])
        
        import_data = [
            {
                "id": existing_id,
                "amount": "9999.99",
                "date": "2024-02-01",
                "description": "Updated bill"
            }
        ]
        
        config = ImportConfig(
            source="test",
            entity=ExportEntity.BILL,
        )
        
        result = await client.import_data(config, import_data)
        
        assert result["updated_count"] == 1
        assert result["imported_count"] == 0
        assert result["failed_count"] == 0
        assert len(client._sample_data[ExportEntity.BILL]) == initial_count
        # Verify the bill was updated
        updated_bill = next(b for b in client._sample_data[ExportEntity.BILL] if b["id"] == existing_id)
        assert updated_bill["amount"] == "9999.99"

    @pytest.mark.asyncio
    async def test_import_data_with_errors(self):
        """Test importing data with validation errors."""
        client = MockSaaSApiClient()
        from app.domain.entities import ImportConfig
        
        # Import data with missing required fields
        import_data = [
            {"description": "Missing amount and date"}  # Missing required fields
        ]
        
        config = ImportConfig(
            source="test",
            entity=ExportEntity.BILL,
        )
        
        result = await client.import_data(config, import_data)
        
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
        
        import_data = [
            {"amount": "500.00", "date": "2024-02-01", "description": "New bill"}
        ]
        
        config = ImportConfig(
            source="test",
            entity=ExportEntity.BILL,
        )
        
        await client.import_data(config, import_data)
        
        # Verify file was created/updated
        assert data_file.exists()
        with open(data_file, "r") as f:
            saved_data = json.load(f)
            assert "bill" in saved_data

    def test_save_data(self, tmp_path):
        """Test saving data to file."""
        data_file = tmp_path / "test_data.json"
        client = MockSaaSApiClient(data_file=str(data_file))
        
        # Modify data
        client._sample_data[ExportEntity.BILL].append({
            "id": "test-id",
            "amount": 100.00,
            "date": "2024-01-01"
        })
        
        client._save_data()
        
        # Verify file was saved
        assert data_file.exists()
        with open(data_file, "r") as f:
            saved_data = json.load(f)
            assert "bill" in saved_data

