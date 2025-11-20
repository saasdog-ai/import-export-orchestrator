# Production Import Flow

This document describes the production-ready multi-phase import process implemented in the import-export-orchestrator service.

## Overview

The import process is split into two distinct phases:

1. **Phase 1: Upload & Validation** - File upload, validation, and storage
2. **Phase 2: Import Execution** - Actual data import with detailed error reporting

This separation ensures that:
- Files are validated before import begins
- Users get immediate feedback on validation errors
- Import errors are clearly identified with row and field information
- Files are stored securely in cloud storage

## Phase 1: Upload & Validation

### Endpoint: `POST /imports/upload`

**Request:**
- `file`: Multipart file upload (CSV or JSON)
- `entity`: Query parameter (default: `bill`) - Entity type to import

**Process:**
1. File is uploaded to a temporary local location
2. **File Format Validation:**
   - Check file extension (.csv or .json)
   - Verify file size (max 10MB)
   - Ensure file is not empty
3. **Content Validation:**
   - **Malicious Input Detection:**
     - SQL injection patterns (`';`, `--`, `/*`, `*/`, `xp_`, `sp_`, `exec`, `union`, `select`)
     - Script injection patterns (`<script`, `javascript:`, `onerror=`, `onclick=`)
   - **Format Validation:**
     - Required fields check (e.g., `amount`, `date` for bills)
     - Field type validation (numbers, dates, UUIDs)
     - Date format validation (YYYY-MM-DD)
   - **Row-by-row validation** with row number tracking
4. If validation passes:
   - File is uploaded to cloud storage (temp location: `imports/{client_id}/temp/{filename}`)
   - Returns file path for Phase 2
5. If validation fails:
   - Returns detailed error list with row and field information
   - File is not stored

**Response (Success):**
```json
{
  "status": "validated",
  "message": "File uploaded and validated successfully",
  "file_path": "imports/{client_id}/temp/{filename}",
  "entity": "bill",
  "filename": "bills.csv"
}
```

**Response (Validation Failed):**
```json
{
  "status": "validation_failed",
  "message": "File validation failed",
  "validation_errors": [
    {
      "row": 2,
      "field": "amount",
      "message": "Field 'amount' must be a number"
    },
    {
      "row": 3,
      "field": "date",
      "message": "Field 'date' must be in YYYY-MM-DD format"
    },
    {
      "row": 5,
      "message": "Potentially malicious content detected in field 'description'"
    }
  ],
  "error_count": 3
}
```

## Phase 2: Import Execution

### Endpoint: `POST /imports/execute`

**Request:**
```json
{
  "file_path": "imports/{client_id}/temp/{filename}",
  "entity": "bill"
}
```

**Process:**
1. Creates an import job definition
2. Starts the import job run
3. Worker thread:
   - Downloads file from cloud storage (if needed)
   - Parses file (CSV or JSON)
   - Imports data row by row
   - Tracks errors with row numbers
   - Updates job run with results

**Response:**
```json
{
  "job_id": "uuid",
  "run_id": "uuid",
  "status": "pending",
  "message": "Import job created and started"
}
```

## Error Reporting

### Validation Errors (Phase 1)

Errors are returned immediately with:
- **Row number** (1-based, header is row 0)
- **Field name** (if applicable)
- **Error message**

Example:
```json
{
  "row": 3,
  "field": "amount",
  "message": "Required field 'amount' is missing or empty"
}
```

### Import Errors (Phase 2)

Errors are stored in the job run's `result_metadata`:
```json
{
  "imported_count": 5,
  "updated_count": 2,
  "failed_count": 1,
  "import_errors": [
    {
      "row": 8,
      "field": "date",
      "message": "Failed to import record: Invalid date format"
    }
  ]
}
```

## Security Features

1. **Malicious Input Detection:**
   - SQL injection patterns
   - Script injection patterns
   - XSS prevention

2. **File Size Limits:**
   - Maximum file size: 10MB
   - Prevents DoS attacks

3. **File Type Validation:**
   - Only CSV and JSON files allowed
   - Extension validation

4. **Authentication:**
   - All endpoints require JWT authentication
   - Client ID extracted from token (not from request body)

## Example Workflow

### Step 1: Upload and Validate

```bash
curl -X POST "http://localhost:8000/imports/upload?entity=bill" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@bills.csv"
```

**If validation fails:**
- User receives immediate feedback with all errors
- Can fix the file and retry

**If validation succeeds:**
- File is stored in cloud storage
- User receives `file_path` for next step

### Step 2: Execute Import

```bash
curl -X POST "http://localhost:8000/imports/execute" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "imports/{client_id}/temp/bills.csv",
    "entity": "bill"
  }'
```

### Step 3: Check Job Status

```bash
curl "http://localhost:8000/jobs/{job_id}/runs/{run_id}" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response includes:**
- Import statistics (created, updated, failed)
- Detailed error list with row/field information
- Job status (succeeded, failed, pending)

## Required Fields by Entity

- **BILL**: `amount`, `date`
- **INVOICE**: `amount`, `date`
- **VENDOR**: `name`
- **PROJECT**: `code`, `name`

## File Format Requirements

### CSV
- UTF-8 encoding
- Header row required
- Comma-separated values
- Date format: YYYY-MM-DD

### JSON
- UTF-8 encoding
- Array of objects or single object
- Date format: YYYY-MM-DD (string)

## Error Handling

1. **Validation Errors (Phase 1):**
   - Returned immediately
   - File is not stored
   - User can fix and retry

2. **Import Errors (Phase 2):**
   - Stored in job run metadata
   - Job status: `failed` if any errors
   - Detailed error list with row/field info

3. **System Errors:**
   - Cloud storage failures
   - File parsing errors
   - Database errors
   - All logged with full stack traces

## Best Practices

1. **Always validate before importing** - Use Phase 1 first
2. **Handle validation errors** - Fix file issues before Phase 2
3. **Monitor job status** - Poll job run status for completion
4. **Check error details** - Review `import_errors` for failed records
5. **Clean up temp files** - Consider implementing cleanup job for old temp files

## Future Enhancements

- [ ] Async file processing for large files
- [ ] Progress tracking during import
- [ ] Partial import support (continue after errors)
- [ ] File cleanup automation (delete temp files after N days)
- [ ] Enhanced validation rules (custom validators per entity)
- [ ] Batch import support (multiple files in one job)

