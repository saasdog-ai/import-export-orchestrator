# Export API Guide - Using curl

This guide walks you through exporting data using the REST APIs with curl commands.

## Prerequisites

1. **Service Running**: The import-export-orchestrator service should be running
   ```bash
   # Check if service is running
   curl http://localhost:8000/health
   ```

2. **Authentication**: The service uses JWT tokens for multi-tenant isolation
   - The `client_id` is extracted from the JWT token (not from URL path parameters)
   - In development mode (auth disabled), a default client_id is used
   - In production, you'll need a valid JWT token with `client_id` claim

## Step-by-Step Export Process

### Step 1: Create an Export Job

Create an export job that will fetch and export data.

**Endpoint**: `POST /exports`

**Request Body**:
```json
{
  "entity": "bill",
  "fields": [
    {"field": "id"},
    {"field": "amount", "as": "Total Amount"},
    {"field": "date", "as": "Bill Date"},
    {"field": "description"},
    {"field": "status", "as": "Payment Status"},
    {"field": "vendor.name", "as": "Vendor Name"}
  ],
  "filters": {
    "operator": "and",
    "filters": [
      {"field": "amount", "operator": "gt", "value": 1000},
      {"field": "status", "operator": "eq", "value": "paid"}
    ]
  },
  "sort": [{"field": "date", "direction": "desc"}],
  "limit": 100,
  "offset": 0
}
```

**curl Command**:
```bash
curl -X POST http://localhost:8000/exports \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "entity": "bill",
    "fields": [
      {"field": "id"},
      {"field": "amount", "as": "Total Amount"},
      {"field": "date", "as": "Bill Date"},
      {"field": "description"},
      {"field": "status", "as": "Payment Status"},
      {"field": "vendor.name", "as": "Vendor Name"}
    ],
    "filters": {
      "operator": "and",
      "filters": [
        {"field": "amount", "operator": "gt", "value": 1000},
        {"field": "status", "operator": "eq", "value": "paid"}
      ]
    },
    "sort": [{"field": "date", "direction": "desc"}],
    "limit": 100,
    "offset": 0
  }'
```

**Response** (201 Created):
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "entity": "bill",
  "status": "pending",
  "result_metadata": null,
  "error_message": null
}
```

**Save the `run_id`** - you'll need it for the next steps.

### Step 2: Check Export Job Status

Check if the export job has completed.

**Endpoint**: `GET /exports/{run_id}/result`

**curl Command**:
```bash
# Replace RUN_ID with the run_id from Step 1
curl -X GET http://localhost:8000/exports/550e8400-e29b-41d4-a716-446655440000/result \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response** (200 OK) - Job Completed:
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "entity": "bill",
  "status": "succeeded",
  "result_metadata": {
    "count": 5,
    "format": "csv",
    "remote_file_path": "exports/00000000-0000-0000-0000-000000000000/550e8400-e29b-41d4-a716-446655440000/abc123.csv"
  },
  "error_message": null
}
```

**Response** (200 OK) - Job Still Running:
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "entity": "bill",
  "status": "running",
  "result_metadata": null,
  "error_message": null
}
```

**Response** (200 OK) - Job Failed:
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "entity": "bill",
  "status": "failed",
  "result_metadata": null,
  "error_message": "Export failed: ..."
}
```

### Step 3: Get Download URL

Once the job status is `succeeded`, get a pre-signed URL to download the file.

**Endpoint**: `GET /exports/{run_id}/download?expiration_seconds=3600`

**curl Command**:
```bash
# Replace RUN_ID with the run_id from Step 1
# expiration_seconds is optional (default: 3600 = 1 hour, max: 604800 = 7 days)
curl -X GET "http://localhost:8000/exports/550e8400-e29b-41d4-a716-446655440000/download?expiration_seconds=3600" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response** (200 OK):
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "download_url": "https://s3.amazonaws.com/bucket/exports/.../file.csv?X-Amz-Signature=...",
  "expires_in_seconds": 3600,
  "file_path": "exports/00000000-0000-0000-0000-000000000000/550e8400-e29b-41d4-a716-446655440000/abc123.csv"
}
```

### Step 4: Download the File

**Option A**: Use the pre-signed `download_url` from Step 3:

```bash
# Replace DOWNLOAD_URL with the URL from Step 3
curl -O "https://s3.amazonaws.com/bucket/exports/.../file.csv?X-Amz-Signature=..."
```

Or save with a specific filename:
```bash
curl -o exported_bills.csv "https://s3.amazonaws.com/bucket/exports/.../file.csv?X-Amz-Signature=..."
```

**Option B**: Download directly through the API (no pre-signed URL needed):

**Endpoint**: `GET /exports/{run_id}/file`

```bash
curl -O -J http://localhost:8000/exports/550e8400-e29b-41d4-a716-446655440000/file \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

This returns the file content directly with appropriate `Content-Disposition` headers.

## Complete Example Script

Here's a complete bash script that does all steps:

```bash
#!/bin/bash

# Configuration
BASE_URL="http://localhost:8000"
JWT_TOKEN="YOUR_JWT_TOKEN"  # Leave empty if auth is disabled
ENTITY="bill"

# Step 1: Create Export Job
echo "Step 1: Creating export job..."
RESPONSE=$(curl -s -X POST "${BASE_URL}/exports" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -d '{
    "entity": "'"${ENTITY}"'",
    "fields": [
      {"field": "id"},
      {"field": "amount", "as": "Total Amount"},
      {"field": "date", "as": "Bill Date"},
      {"field": "description"},
      {"field": "status", "as": "Payment Status"}
    ],
    "filters": {
      "operator": "and",
      "filters": [
        {"field": "amount", "operator": "gt", "value": 1000}
      ]
    },
    "sort": [{"field": "date", "direction": "desc"}],
    "limit": 100,
    "offset": 0
  }')

# Extract run_id from response
RUN_ID=$(echo $RESPONSE | grep -o '"run_id":"[^"]*"' | cut -d'"' -f4)
echo "Export job created. Run ID: ${RUN_ID}"

# Step 2: Wait for job to complete
echo "Step 2: Waiting for export to complete..."
MAX_WAIT=30
WAIT_COUNT=0
STATUS="pending"

while [ "$STATUS" != "succeeded" ] && [ "$STATUS" != "failed" ] && [ $WAIT_COUNT -lt $MAX_WAIT ]; do
  sleep 2
  WAIT_COUNT=$((WAIT_COUNT + 2))
  
  RESULT=$(curl -s -X GET "${BASE_URL}/exports/${RUN_ID}/result" \
    -H "Authorization: Bearer ${JWT_TOKEN}")
  
  STATUS=$(echo $RESULT | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
  echo "  Status: ${STATUS} (waited ${WAIT_COUNT}s)"
done

if [ "$STATUS" == "failed" ]; then
  echo "Export failed!"
  echo $RESULT | python3 -m json.tool
  exit 1
fi

# Step 3: Get Download URL
echo "Step 3: Getting download URL..."
DOWNLOAD_RESPONSE=$(curl -s -X GET "${BASE_URL}/exports/${RUN_ID}/download?expiration_seconds=3600" \
  -H "Authorization: Bearer ${JWT_TOKEN}")

DOWNLOAD_URL=$(echo $DOWNLOAD_RESPONSE | grep -o '"download_url":"[^"]*"' | cut -d'"' -f4)
echo "Download URL obtained"

# Step 4: Download the file
echo "Step 4: Downloading file..."
OUTPUT_FILE="exported_${ENTITY}_$(date +%Y%m%d_%H%M%S).csv"
curl -o "${OUTPUT_FILE}" "${DOWNLOAD_URL}"
echo "File downloaded: ${OUTPUT_FILE}"
```

## Alternative: Preview Before Exporting

You can preview the data before creating an export job:

**Endpoint**: `POST /exports/preview`

**curl Command**:
```bash
curl -X POST http://localhost:8000/exports/preview \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "entity": "bill",
    "fields": [
      {"field": "id"},
      {"field": "amount", "as": "Total Amount"},
      {"field": "date", "as": "Bill Date"}
    ],
    "filters": {
      "operator": "and",
      "filters": [
        {"field": "amount", "operator": "gt", "value": 1000}
      ]
    },
    "sort": [{"field": "date", "direction": "desc"}],
    "limit": 20,
    "offset": 0
  }'
```

**Response** (200 OK):
```json
{
  "entity": "bill",
  "count": 5,
  "records": [
    {"id": "...", "Total Amount": 2500.0, "Bill Date": "2024-01-20"},
    {"id": "...", "Total Amount": 1000.5, "Bill Date": "2024-01-15"}
  ],
  "limit": 20,
  "offset": 0
}
```

Note: The response uses the aliased field names (e.g., "Total Amount" instead of "amount").

## Available Entities

- `bill` - Bills
- `invoice` - Invoices
- `vendor` - Vendors
- `project` - Projects

## Available Filter Operators

- `eq` - Equals
- `ne` - Not equals
- `gt` - Greater than
- `gte` - Greater than or equal
- `lt` - Less than
- `lte` - Less than or equal
- `in` - In list
- `between` - Between two values
- `contains` - Contains substring (case-insensitive)
- `startswith` - Starts with
- `endswith` - Ends with

## Filter Examples

### Simple Filter
```json
{
  "operator": "and",
  "filters": [
    {"field": "amount", "operator": "gt", "value": 1000}
  ]
}
```

### Multiple Filters (AND)
```json
{
  "operator": "and",
  "filters": [
    {"field": "amount", "operator": "gt", "value": 1000},
    {"field": "status", "operator": "eq", "value": "paid"}
  ]
}
```

### Multiple Filters (OR)
```json
{
  "operator": "or",
  "filters": [
    {"field": "amount", "operator": "gt", "value": 2000},
    {"field": "status", "operator": "eq", "value": "pending"}
  ]
}
```

### Nested Field Filter
```json
{
  "operator": "and",
  "filters": [
    {"field": "vendor.name", "operator": "contains", "value": "Acme"}
  ]
}
```

### BETWEEN Filter
```json
{
  "operator": "and",
  "filters": [
    {"field": "amount", "operator": "between", "value": [500, 2000]}
  ]
}
```

### IN Filter
```json
{
  "operator": "and",
  "filters": [
    {"field": "status", "operator": "in", "value": ["paid", "pending"]}
  ]
}
```

## Sorting Examples

### Single Field Sort
```json
[{"field": "date", "direction": "desc"}]
```

### Multiple Field Sort
```json
[
  {"field": "date", "direction": "desc"},
  {"field": "amount", "direction": "asc"}
]
```

## Authentication

### Development Mode (Auth Disabled)

If authentication is disabled, you can omit the Authorization header or use an empty token:

```bash
curl -X POST http://localhost:8000/exports \
  -H "Content-Type: application/json" \
  -d '{...}'
```

The service will use a default client_id: `00000000-0000-0000-0000-000000000000`

### Production Mode (Auth Enabled)

In production, you need a valid JWT token:

```bash
# Get token from your auth service
JWT_TOKEN=$(curl -X POST https://auth.example.com/token \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}' | jq -r '.token')

# Use token in export request
curl -X POST http://localhost:8000/exports \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -d '{...}'
```

The JWT token should contain a `client_id` claim (or `sub` claim used as client_id).

## Error Handling

### 400 Bad Request
```json
{
  "detail": "Field 'invalid_field' is not allowed for entity 'bill'"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated. Valid JWT token with client_id claim required."
}
```

### 403 Forbidden
```json
{
  "detail": "Access denied. Job does not belong to authenticated client."
}
```

### 404 Not Found
```json
{
  "detail": "Job run not found"
}
```

## Troubleshooting

### Job Status Stays "pending"
- Check if the job runner workers are running
- Check application logs: `docker logs job_runner_app`
- Verify the job was queued successfully

### Download URL Returns 404
- Ensure the job status is `succeeded`
- Check that `remote_file_path` exists in `result_metadata`
- Verify cloud storage is configured correctly

### No Data Returned
- Check your filters - they might be too restrictive
- Verify the entity has data in the system
- Try a preview first to see what data is available

### Authentication Errors
- Verify JWT token is valid and not expired
- Check that token contains `client_id` or `sub` claim
- In development, ensure auth is disabled or use default client_id

## Field Definitions

Fields are specified as an array of field definition objects. Each field definition supports:

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `field` | string | Yes | Source field path (e.g., `"amount"`, `"vendor.name"`) |
| `as` | string | No | Output alias for the field (e.g., `"Total Amount"`) |
| `format` | string | No | Reserved for future transformations (e.g., date formatting) |

### Field Definition Examples

**Simple fields (no alias)**:
```json
{
  "fields": [
    {"field": "id"},
    {"field": "amount"},
    {"field": "date"}
  ]
}
```

Output CSV headers: `id,amount,date`

**Fields with aliases**:
```json
{
  "fields": [
    {"field": "id", "as": "Bill ID"},
    {"field": "amount", "as": "Total Amount"},
    {"field": "date", "as": "Bill Date"},
    {"field": "vendor.name", "as": "Vendor Name"}
  ]
}
```

Output CSV headers: `Bill ID,Total Amount,Bill Date,Vendor Name`

**Mixed (some with aliases, some without)**:
```json
{
  "fields": [
    {"field": "id"},
    {"field": "amount", "as": "Total"},
    {"field": "status"}
  ]
}
```

Output CSV headers: `id,Total,status`

### Field Order

The order of fields in the array determines the column order in the exported file:

```json
{
  "fields": [
    {"field": "vendor.name", "as": "Vendor"},
    {"field": "amount", "as": "Amount"},
    {"field": "id"}
  ]
}
```

Output CSV: `Vendor,Amount,id` (in that order)

### Available Fields by Entity

**bill**:
- Simple: `id`, `amount`, `date`, `description`, `status`, `created_at`
- Nested: `vendor.id`, `vendor.name`, `vendor.email`, `project.id`, `project.code`, `project.name`

**invoice**:
- Simple: `id`, `amount`, `date`, `due_date`, `description`, `status`, `created_at`
- Nested: `vendor.id`, `vendor.name`, `vendor.email`, `project.id`, `project.code`, `project.name`

**vendor**:
- Simple: `id`, `name`, `email`, `phone`, `address`, `created_at`
- Nested: `project.id`, `project.code`, `project.name`

**project**:
- Simple: `id`, `code`, `name`, `description`, `status`, `created_at`

## Quick Reference

```bash
# Health check
curl http://localhost:8000/health

# Create export with field aliases
curl -X POST http://localhost:8000/exports \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "entity": "bill",
    "fields": [
      {"field": "id"},
      {"field": "amount", "as": "Total Amount"}
    ],
    "limit": 10
  }'

# Check status
curl http://localhost:8000/exports/{RUN_ID}/result \
  -H "Authorization: Bearer TOKEN"

# Get download URL
curl "http://localhost:8000/exports/{RUN_ID}/download" \
  -H "Authorization: Bearer TOKEN"

# Download file
curl -O "{DOWNLOAD_URL}"
```

