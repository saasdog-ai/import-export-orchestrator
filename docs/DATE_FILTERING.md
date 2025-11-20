# Date Filtering for Jobs and Job Runs

Both job and job run endpoints now support date filtering to help manage large result sets.

## Endpoints with Date Filtering

### 1. GET /jobs/{job_id}/runs

Get all runs for a specific job, optionally filtered by date range.

**Query Parameters:**
- `start_date` (optional): ISO 8601 datetime - Filter runs created **after** this date/time
- `end_date` (optional): ISO 8601 datetime - Filter runs created **before** this date/time

**Examples:**

```bash
# Get all runs for a job
curl "http://localhost:8000/jobs/{job_id}/runs"

# Get runs created after January 1, 2024
curl "http://localhost:8000/jobs/{job_id}/runs?start_date=2024-01-01T00:00:00Z"

# Get runs created in 2024
curl "http://localhost:8000/jobs/{job_id}/runs?start_date=2024-01-01T00:00:00Z&end_date=2024-12-31T23:59:59Z"

# Get runs from the last 7 days
curl "http://localhost:8000/jobs/{job_id}/runs?start_date=2024-11-13T00:00:00Z"
```

### 2. GET /jobs

Get all jobs for the authenticated client, optionally filtered by date range.

**Query Parameters:**
- `start_date` (optional): ISO 8601 datetime - Filter jobs created **after** this date/time
- `end_date` (optional): ISO 8601 datetime - Filter jobs created **before** this date/time

**Examples:**

```bash
# Get all jobs for the authenticated client
curl "http://localhost:8000/jobs"

# Get jobs created after January 1, 2024
curl "http://localhost:8000/jobs?start_date=2024-01-01T00:00:00Z"

# Get jobs created in 2024
curl "http://localhost:8000/jobs?start_date=2024-01-01T00:00:00Z&end_date=2024-12-31T23:59:59Z"

# Get jobs from the last 30 days
curl "http://localhost:8000/jobs?start_date=2024-10-21T00:00:00Z"
```

## Date Format

All date parameters use **ISO 8601** format with UTC timezone:

- Format: `YYYY-MM-DDTHH:MM:SSZ`
- Examples:
  - `2024-01-01T00:00:00Z` (January 1, 2024, midnight UTC)
  - `2024-12-31T23:59:59Z` (December 31, 2024, 11:59:59 PM UTC)
  - `2024-11-20T14:30:00Z` (November 20, 2024, 2:30 PM UTC)

## Filtering Logic

- **start_date only**: Returns all records created **on or after** the start_date
- **end_date only**: Returns all records created **on or before** the end_date
- **Both dates**: Returns all records created **between** start_date and end_date (inclusive)
- **No dates**: Returns all records (no filtering)

## Use Cases

### Get Recent Activity
```bash
# Get runs from the last 24 hours
start_date=$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)
curl "http://localhost:8000/jobs/{job_id}/runs?start_date=${start_date}"
```

### Get Monthly Reports
```bash
# Get all runs for November 2024
curl "http://localhost:8000/jobs/{job_id}/runs?start_date=2024-11-01T00:00:00Z&end_date=2024-11-30T23:59:59Z"
```

### Get Jobs Created This Week
```bash
# Get jobs created in the last 7 days
start_date=$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ)
curl "http://localhost:8000/jobs?start_date=${start_date}"
```

## Performance Considerations

- Date filtering is performed at the database level for optimal performance
- Results are ordered by `created_at` in descending order (newest first)
- Indexes on `created_at` columns ensure fast queries even with large datasets

## Response Format

The response format remains unchanged - you'll receive a list of job runs or job definitions, filtered by the date criteria:

```json
[
  {
    "id": "uuid",
    "job_id": "uuid",
    "status": "succeeded",
    "created_at": "2024-11-20T14:30:00Z",
    "started_at": "2024-11-20T14:30:01Z",
    "completed_at": "2024-11-20T14:30:05Z",
    ...
  }
]
```

