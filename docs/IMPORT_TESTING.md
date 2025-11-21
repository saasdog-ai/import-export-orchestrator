# Import Testing Guide

## Overview

This guide explains how to test import functionality and the different approaches for storing mock data.

## Current Implementation

### Stateful Mock Client

The `MockSaaSApiClient` has been enhanced to:
- **Store imported data in memory** - Data persists during the application lifecycle
- **Support create/update operations** - If a record has an `id` that exists, it updates; otherwise creates new
- **Optional JSON file persistence** - Can save/load data from a JSON file

### Import Flow

1. **CSV/JSON File** → `FileParser.parse_file()` → List of dictionaries
2. **Data** → `MockSaaSApiClient.import_data()` → Creates/updates records
3. **Verification** → Export bills to verify they were imported

## Testing Options Comparison

### Option 1: In-Memory (Current Default) ✅ **Recommended for Unit Tests**

**Pros:**
- ✅ Fast - No I/O operations
- ✅ Isolated - Each test gets fresh data
- ✅ Simple - No file management
- ✅ Works well with pytest fixtures

**Cons:**
- ❌ Data lost on restart
- ❌ Not persistent across test runs

**Best For:**
- Unit tests
- Fast iteration during development
- CI/CD pipelines

**Usage:**
```python
# Default - in-memory only
client = MockSaaSApiClient()
```

### Option 2: JSON File ✅ **Recommended for Integration Tests**

**Pros:**
- ✅ Persistent - Data survives restarts
- ✅ Version controllable - Can commit test data to git
- ✅ Human readable - Easy to inspect/edit
- ✅ Fast enough for integration tests

**Cons:**
- ❌ File I/O overhead
- ❌ Need to manage file paths
- ❌ Not as realistic as DB

**Best For:**
- Integration tests
- Manual testing
- Test data that needs to be shared

**Usage:**
```python
# With JSON file persistence
client = MockSaaSApiClient(data_file="tests/fixtures/mock_data.json")
```

### Option 3: Database Table ❌ **Not Recommended for Mock Data**

**Pros:**
- ✅ Most realistic
- ✅ Can test transactions
- ✅ Supports complex queries

**Cons:**
- ❌ Much slower
- ❌ Requires DB setup/teardown
- ❌ More complex
- ❌ Overkill for mocking

**Best For:**
- End-to-end tests with real database
- Production-like testing environments

**Recommendation:** Use a separate test database, not the mock client.

## Recommended Approach

### For Unit Tests
```python
# Use in-memory mock (default)
@pytest.fixture
def mock_saas_client():
    return MockSaaSApiClient()  # In-memory, fresh for each test
```

### For Integration Tests
```python
# Use JSON file for persistence
@pytest.fixture
def mock_saas_client():
    data_file = "tests/fixtures/test_data.json"
    return MockSaaSApiClient(data_file=data_file)
```

### For Manual Testing
```python
# In dependency_injection.py, you can configure:
_saas_client = MockSaaSApiClient(
    data_file=settings.mock_data_file  # Optional env var
)
```

## Testing Import from CSV

### 1. Create a CSV File

```csv
id,amount,date,description,status
,1500.00,2024-02-01,New office furniture,paid
,2200.50,2024-02-05,Marketing campaign,pending
existing-bill-id,1000.50,2024-01-15,Updated office supplies,paid
```

**Notes:**
- Empty `id` = create new record
- Existing `id` = update record
- All other fields map to bill properties

### 2. Create Import Job via API

```python
import httpx

job_data = {
    "name": "Import Bills from CSV",
    "job_type": "import",
    "import_config": {
        "source": "csv_file",
        "entity": "bill",
        "options": {
            "source_file": "/path/to/bills.csv"  # Absolute path
        }
    },
    "enabled": True,
}

response = httpx.post("http://localhost:8000/jobs", json=job_data)
```

### 3. Run the Import Job

```python
job_id = response.json()["id"]
run_response = httpx.post(f"http://localhost:8000/jobs/{job_id}/run")
```

### 4. Verify Import

```python
# Export bills to see imported data
export_request = {
    "entity": "bill",
    "fields": ["id", "amount", "date", "description", "status"],
    "limit": 100,
}
export_response = httpx.post("http://localhost:8000/exports", json=export_request)
```

## Example Test Script

See `scripts/examples/test_import.py` for a complete example that:
1. Creates an import job from CSV
2. Runs the import
3. Verifies the data was imported
4. Exports bills to confirm

## File Structure

```
tests/
├── fixtures/
│   ├── sample_bills.csv          # Sample CSV for imports
│   └── mock_data.json            # Optional: persistent mock data
└── unit/
    └── test_imports.py            # Unit tests with in-memory mocks
```

## Environment Variables

You can configure mock data file via environment:

```bash
export MOCK_DATA_FILE="tests/fixtures/mock_data.json"
```

Then in `app/core/config.py`:
```python
mock_data_file: Optional[str] = Field(default=None, description="Path to JSON file for mock data")
```

## Summary

**For Testing Imports:**
1. ✅ **Unit Tests**: Use in-memory `MockSaaSApiClient()` (fast, isolated)
2. ✅ **Integration Tests**: Use JSON file `MockSaaSApiClient(data_file="...")` (persistent)
3. ❌ **Don't use DB table** for mock data (use real DB for E2E tests instead)

**The current implementation supports all three approaches**, but JSON file is the sweet spot for testing imports while keeping tests fast and maintainable.

