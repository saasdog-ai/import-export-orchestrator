# Environment Variables

This document describes all environment variables used by the Import/Export Orchestrator service.

---

## Required Variables

### Database
- **`DATABASE_URL`** (default: `postgresql+asyncpg://postgres:postgres@localhost:5432/job_runner`)
  - PostgreSQL connection string
  - Format: `postgresql+asyncpg://user:password@host:port/database`

---

## Optional Variables

### Application
- **`APP_NAME`** (default: `import-export-orchestrator`)
  - Application name used in API responses

- **`APP_ENV`** (default: `development`)
  - Environment mode: `development` or `production`
  - In `production`, additional validation is enforced:
    - Message queue is required
    - Cloud storage bucket required if cloud provider is set

- **`LOG_LEVEL`** (default: `INFO`)
  - Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`

### API
- **`API_HOST`** (default: `0.0.0.0`)
  - Host to bind the API server

- **`API_PORT`** (default: `8000`)
  - Port for the API server

- **`API_RELOAD`** (default: `false`)
  - Enable auto-reload for development

### CORS
- **`ALLOWED_ORIGINS`** (default: `["*"]`)
  - Comma-separated list of allowed CORS origins
  - **⚠️ Security:** Use specific domains in production, not `*`
  - Example: `http://localhost:3000,https://app.example.com`

### Database Pool
- **`DATABASE_POOL_SIZE`** (default: `10`)
  - Number of connections to maintain in the pool

- **`DATABASE_MAX_OVERFLOW`** (default: `20`)
  - Maximum number of connections to create beyond pool_size

- **`DATABASE_POOL_RECYCLE`** (default: `3600`)
  - Seconds after which a connection is recycled (1 hour)

- **`DATABASE_POOL_TIMEOUT`** (default: `30`)
  - Seconds to wait for a connection from the pool

### Security (JWT - Currently Disabled)
- **`JWT_SECRET_KEY`** (default: `CHANGE_THIS_IN_PRODUCTION`)
  - Secret key for JWT token signing
  - **⚠️ Security:** Must be changed in production

- **`JWT_ALGORITHM`** (default: `HS256`)
  - JWT signing algorithm

- **`JWT_ACCESS_TOKEN_EXPIRE_MINUTES`** (default: `30`)
  - Token expiration time in minutes

### Scheduler
- **`SCHEDULER_ENABLED`** (default: `true`)
  - Enable/disable job scheduler

- **`SCHEDULER_TIMEZONE`** (default: `UTC`)
  - Timezone for cron schedules

### Job Runner
- **`JOB_RUNNER_MAX_WORKERS`** (default: `5`)
  - Maximum number of concurrent worker threads

- **`JOB_RUNNER_QUEUE_SIZE`** (default: `100`)
  - Size of in-memory job queue (development only)

### Cloud Storage

#### AWS S3
- **`CLOUD_PROVIDER`** (default: `None`)
  - Set to `aws` to use S3
  - Options: `aws`, `azure`, `gcp`, or `None`

- **`CLOUD_STORAGE_BUCKET`** (default: `None`)
  - S3 bucket name for file storage

- **`AWS_REGION`** (default: `None`)
  - AWS region (e.g., `us-east-1`)
  - Can use IAM roles instead of credentials

- **`AWS_ACCESS_KEY_ID`** (default: `None`)
  - AWS access key (not recommended - use IAM roles)

- **`AWS_SECRET_ACCESS_KEY`** (default: `None`)
  - AWS secret key (not recommended - use IAM roles)

#### Azure Blob Storage
- **`CLOUD_PROVIDER`** = `azure`
- **`CLOUD_STORAGE_BUCKET`** = Container name
- **`AZURE_STORAGE_ACCOUNT_NAME`** = Storage account name
- Uses Azure Managed Identity (recommended) or connection string

#### Google Cloud Storage
- **`CLOUD_PROVIDER`** = `gcp`
- **`CLOUD_STORAGE_BUCKET`** = GCS bucket name
- Uses Application Default Credentials (recommended) or service account key

### Message Queue

#### AWS SQS
- **`CLOUD_PROVIDER`** = `aws`
- **`MESSAGE_QUEUE_NAME`** = SQS queue name
- **`MESSAGE_QUEUE_WAIT_TIME`** (default: `20`)
  - Long polling wait time in seconds
- **`MESSAGE_QUEUE_MAX_MESSAGES`** (default: `1`)
  - Max messages per receive call

#### Azure Queue Storage
- **`CLOUD_PROVIDER`** = `azure`
- **`MESSAGE_QUEUE_NAME`** = Queue name
- Uses Azure Managed Identity

#### Google Cloud Pub/Sub
- **`CLOUD_PROVIDER`** = `gcp`
- **`MESSAGE_QUEUE_NAME`** = Topic name
- Uses Application Default Credentials

### Export Settings
- **`EXPORT_FILE_FORMAT`** (default: `csv`)
  - Default export format: `csv` or `json`

- **`EXPORT_LOCAL_PATH`** (default: `/tmp/exports`)
  - Local directory for temporary export files

- **`PRESIGNED_URL_EXPIRATION`** (default: `3600`)
  - Pre-signed URL expiration in seconds (1 hour)

---

## Production Configuration Example

```bash
# Application
APP_ENV=production
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://user:password@rds-host:5432/dbname
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# CORS (specific domains only)
ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com

# Security
JWT_SECRET_KEY=<strong-random-secret>
JWT_ALGORITHM=HS256

# Cloud Storage (AWS)
CLOUD_PROVIDER=aws
CLOUD_STORAGE_BUCKET=my-export-bucket
AWS_REGION=us-east-1
# Use IAM roles instead of access keys

# Message Queue (AWS SQS)
MESSAGE_QUEUE_NAME=job-queue
MESSAGE_QUEUE_WAIT_TIME=20

# Export Settings
EXPORT_FILE_FORMAT=csv
PRESIGNED_URL_EXPIRATION=3600
```

---

## Development Configuration Example

```bash
# Application
APP_ENV=development
LOG_LEVEL=DEBUG

# Database (local Docker)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/job_runner

# CORS (allow all for development)
ALLOWED_ORIGINS=*

# Cloud Storage (optional - files saved locally)
# CLOUD_PROVIDER=
# CLOUD_STORAGE_BUCKET=

# Message Queue (optional - uses in-memory queue)
# MESSAGE_QUEUE_NAME=
```

---

## Validation

When `APP_ENV=production`, the following validations are enforced:

1. **Message Queue Required**
   - `MESSAGE_QUEUE_NAME` must be set
   - In-memory queue is not allowed

2. **Cloud Storage**
   - If `CLOUD_PROVIDER` is set, `CLOUD_STORAGE_BUCKET` must be set

3. **CORS**
   - `ALLOWED_ORIGINS` should not be `*` (warning only)

---

## Docker Compose

Environment variables can be set in `docker-compose.yml`:

```yaml
services:
  app:
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/job_runner
      APP_ENV: development
      ALLOWED_ORIGINS: "*"
```

Or use a `.env` file (not committed to git):

```bash
# .env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/job_runner
APP_ENV=development
ALLOWED_ORIGINS=*
```

---

## Notes

- All environment variables are optional except `DATABASE_URL` (which has a default)
- Defaults are suitable for local development
- Production requires explicit configuration
- Secrets should be managed via:
  - AWS Secrets Manager
  - Azure Key Vault
  - Google Secret Manager
  - Environment variables (less secure, but simpler)

