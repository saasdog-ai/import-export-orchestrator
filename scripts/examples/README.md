# Example Scripts

This directory contains example scripts and test utilities for the Import/Export Orchestrator service.

## Scripts

### `run_sample_export.py`
Creates and runs a sample export job to demonstrate the export functionality.

**Usage:**
```bash
python scripts/examples/run_sample_export.py
```

**What it does:**
- Creates an export job for bills
- Triggers the export
- Polls for completion
- Retrieves the download URL

### `test_import.py`
Tests the import functionality by executing an import job from a local CSV file.

**Usage:**
```bash
python scripts/examples/test_import.py
```

**What it does:**
- Calls `POST /imports/execute` with a local CSV file path
- Polls for job completion
- Verifies by exporting and checking record count

**Note:** In production, the import flow uses presigned URLs (`/imports/request-upload` → direct upload to cloud → `/imports/confirm-upload` → `/imports/execute`). This script uses local file paths for simplicity.

### `test_import_validation.py`
Tests the multi-phase import validation system with both valid and invalid inputs.

**Usage:**
```bash
python scripts/examples/test_import_validation.py
```

**What it does:**
- Tests valid CSV import
- Tests invalid CSV (bad data, malicious content)
- Tests missing required fields
- Verifies detailed error reporting

### `test_scheduled_export.py`
Tests scheduled export jobs using cron expressions.

**Usage:**
```bash
python scripts/examples/test_scheduled_export.py
```

**What it does:**
- Creates a scheduled export job
- Monitors job runs
- Displays status and results

### `check_job_status.py`
Quick utility to check the status of a job run by run_id.

**Usage:**
```bash
python scripts/examples/check_job_status.py <run_id>
```

**What it does:**
- Queries the API for job run status
- Displays status, metadata, and download URL if available

## Prerequisites

1. The service must be running (via Docker Compose or locally)
2. The API should be accessible at `http://localhost:8000`
3. Required Python packages: `httpx`, `asyncio`

## Notes

- These scripts are for **development and testing purposes only**
- They use the default client ID when authentication is disabled
- In production, you would need valid JWT tokens for authentication
- Some scripts may need to be run from the project root directory due to relative imports

