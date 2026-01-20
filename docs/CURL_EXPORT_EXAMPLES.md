# Export API - curl Command Examples

Quick reference for exporting data using curl commands.

## Prerequisites

Service should be running at `http://localhost:8000`

```bash
# Check health
curl http://localhost:8000/health
```

## Step 1: Create Export Job

**Basic Export (No Filters)**
```bash
curl -X POST http://localhost:8000/exports \
  -H "Content-Type: application/json" \
  -d '{
    "entity": "bill",
    "fields": ["id", "amount", "date", "description", "status"],
    "limit": 100
  }'
```

**Export with Filters**
```bash
curl -X POST http://localhost:8000/exports \
  -H "Content-Type: application/json" \
  -d '{
    "entity": "bill",
    "fields": ["id", "amount", "date", "status"],
    "filters": {
      "operator": "and",
      "filters": [
        {"field": "amount", "operator": "gt", "value": 1000},
        {"field": "status", "operator": "eq", "value": "paid"}
      ]
    },
    "sort": [{"field": "date", "direction": "desc"}],
    "limit": 100
  }'
```

**Export with Nested Fields**
```bash
curl -X POST http://localhost:8000/exports \
  -H "Content-Type: application/json" \
  -d '{
    "entity": "bill",
    "fields": ["id", "amount", "date", "vendor.name", "project.code"],
    "filters": {
      "operator": "and",
      "filters": [
        {"field": "vendor.name", "operator": "contains", "value": "Acme"}
      ]
    },
    "limit": 100
  }'
```

**Response:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "entity": "bill",
  "status": "pending",
  "result_metadata": null,
  "error_message": null
}
```

**Save the `run_id` for next steps!**

## Step 2: Check Job Status

Wait a few seconds, then check if the job completed:

```bash
# Replace RUN_ID with the run_id from Step 1
curl http://localhost:8000/exports/550e8400-e29b-41d4-a716-446655440000/result
```

**Response (Job Completed):**
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

**Response (Still Running):**
```json
{
  "status": "running",
  ...
}
```

**Response (Failed):**
```json
{
  "status": "failed",
  "error_message": "Export failed: ..."
}
```

## Step 3: Get Download URL

Once status is `succeeded`, get the download URL:

```bash
# Replace RUN_ID with your run_id
curl "http://localhost:8000/exports/550e8400-e29b-41d4-a716-446655440000/download?expiration_seconds=3600"
```

**Response:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "download_url": "https://s3.amazonaws.com/bucket/exports/.../file.csv?X-Amz-Signature=...",
  "expires_in_seconds": 3600,
  "file_path": "exports/00000000-0000-0000-0000-000000000000/550e8400-e29b-41d4-a716-446655440000/abc123.csv"
}
```

## Step 4: Download the File

Use the `download_url` from Step 3:

```bash
# Replace DOWNLOAD_URL with the URL from Step 3
curl -o exported_bills.csv "https://s3.amazonaws.com/bucket/exports/.../file.csv?X-Amz-Signature=..."
```

Or if no cloud storage is configured, the file is stored locally in the container:
```bash
# Check the local_file_path in result_metadata
docker exec job_runner_app cat /tmp/exports/export_*.csv
```

## Complete Example (All Steps)

```bash
# Step 1: Create export
RESPONSE=$(curl -s -X POST http://localhost:8000/exports \
  -H "Content-Type: application/json" \
  -d '{
    "entity": "bill",
    "fields": ["id", "amount", "date"],
    "limit": 10
  }')

# Extract run_id
RUN_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['run_id'])")

echo "Export job created. Run ID: $RUN_ID"

# Step 2: Wait and check status
sleep 3
STATUS_RESPONSE=$(curl -s http://localhost:8000/exports/$RUN_ID/result)
STATUS=$(echo $STATUS_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")

echo "Job status: $STATUS"

# Step 3: Get download URL (if succeeded)
if [ "$STATUS" == "succeeded" ]; then
  DOWNLOAD_RESPONSE=$(curl -s "http://localhost:8000/exports/$RUN_ID/download")
  DOWNLOAD_URL=$(echo $DOWNLOAD_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['download_url'])")
  
  # Step 4: Download file
  curl -o exported_bills.csv "$DOWNLOAD_URL"
  echo "File downloaded: exported_bills.csv"
fi
```

## Preview Before Exporting

Preview data before creating an export job:

```bash
curl -X POST http://localhost:8000/exports/preview \
  -H "Content-Type: application/json" \
  -d '{
    "entity": "bill",
    "fields": ["id", "amount", "date"],
    "filters": {
      "operator": "and",
      "filters": [
        {"field": "amount", "operator": "gt", "value": 1000}
      ]
    },
    "limit": 20
  }'
```

## Filter Examples

### Amount Greater Than
```json
{
  "filters": {
    "operator": "and",
    "filters": [
      {"field": "amount", "operator": "gt", "value": 1000}
    ]
  }
}
```

### Multiple Conditions (AND)
```json
{
  "filters": {
    "operator": "and",
    "filters": [
      {"field": "amount", "operator": "gt", "value": 1000},
      {"field": "status", "operator": "eq", "value": "paid"}
    ]
  }
}
```

### OR Condition
```json
{
  "filters": {
    "operator": "or",
    "filters": [
      {"field": "amount", "operator": "gt", "value": 2000},
      {"field": "status", "operator": "eq", "value": "pending"}
    ]
  }
}
```

### BETWEEN
```json
{
  "filters": {
    "operator": "and",
    "filters": [
      {"field": "amount", "operator": "between", "value": [500, 2000]}
    ]
  }
}
```

### IN List
```json
{
  "filters": {
    "operator": "and",
    "filters": [
      {"field": "status", "operator": "in", "value": ["paid", "pending"]}
    ]
  }
}
```

### Contains (String Search)
```json
{
  "filters": {
    "operator": "and",
    "filters": [
      {"field": "description", "operator": "contains", "value": "Office"}
    ]
  }
}
```

### Nested Field Filter
```json
{
  "filters": {
    "operator": "and",
    "filters": [
      {"field": "vendor.name", "operator": "contains", "value": "Acme"}
    ]
  }
}
```

## Sorting Examples

### Single Field
```json
{
  "sort": [{"field": "date", "direction": "desc"}]
}
```

### Multiple Fields
```json
{
  "sort": [
    {"field": "date", "direction": "desc"},
    {"field": "amount", "direction": "asc"}
  ]
}
```

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
- `contains` - Contains substring
- `startswith` - Starts with
- `endswith` - Ends with

## Authentication

In development mode (auth disabled), you can omit the Authorization header.

In production, include JWT token:
```bash
curl -X POST http://localhost:8000/exports \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{...}'
```

## Troubleshooting

**Job stays "pending"**: Wait a few more seconds, check logs: `docker logs job_runner_app`

**No download URL**: Check if cloud storage is configured. File may be stored locally.

**Empty results**: Check your filters - they might be too restrictive. Try preview first.

