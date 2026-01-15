"""Unit tests for SaaS client.

NOTE: These tests were written for an older file-based MockSaaSApiClient implementation.
The current implementation uses a database connection (MockSaaSApiClient(db)).
For database-backed testing, see integration tests in tests/integration/.
The SaaS client interface is mocked in query engine tests (test_query_engine.py).
"""

import pytest

# These tests are skipped because MockSaaSApiClient now requires a database connection.
# The file-based implementation (data_file parameter, _save_data method) has been removed.
# For testing the SaaS client interface, see:
# - tests/unit/test_query_engine.py (mocked interface)
# - tests/integration/test_api.py (full integration tests)

pytestmark = pytest.mark.skip(
    reason="MockSaaSApiClient now requires database connection. "
    "These tests were for the obsolete file-based implementation. "
    "See test_query_engine.py for mocked interface tests."
)


class TestMockSaaSApiClient:
    """Test cases for MockSaaSApiClient (skipped - obsolete file-based tests)."""

    def test_init_without_data_file(self):
        """Test client initialization without data file."""
        pass

    def test_init_with_data_file(self, tmp_path):
        """Test client initialization with data file."""
        pass

    def test_init_with_nonexistent_data_file(self):
        """Test client initialization with non-existent data file."""
        pass

    @pytest.mark.asyncio
    async def test_fetch_data_basic(self):
        """Test basic data fetching with client_id filtering."""
        pass

    @pytest.mark.asyncio
    async def test_fetch_data_with_filters(self):
        """Test data fetching with filters and client_id."""
        pass

    @pytest.mark.asyncio
    async def test_import_data_create_new(self):
        """Test importing new records with client_id."""
        pass

    @pytest.mark.asyncio
    async def test_import_data_update_existing(self):
        """Test importing with existing ID (update) and client_id."""
        pass

    @pytest.mark.asyncio
    async def test_import_data_with_errors(self):
        """Test importing data with validation errors and client_id."""
        pass

    @pytest.mark.asyncio
    async def test_import_data_saves_to_file(self, tmp_path):
        """Test that import data is saved to file when data_file is set."""
        pass

    def test_save_data(self, tmp_path):
        """Test saving data to file."""
        pass
