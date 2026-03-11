# Import-Export Orchestrator

A production-ready backend for asynchronous import/export operations with scheduling, cloud storage, and multi-tenant isolation.

## Why This Project?

Every SaaS application needs import/export. Users need to export filtered data to CSV, import spreadsheets of records, and schedule recurring exports. This project gives you a production-ready starting point instead of building from scratch -- and it's designed to be extended with AI coding tools like Claude Code.

**This is the companion to [integration-platform](https://github.com/saasdog-ai/integration-platform).** Together, they cover the two fundamental integration patterns: this project handles **file-based integrations** (CSV import/export, bulk operations, scheduled reports), while integration-platform handles **API-based integrations** (real-time sync with ERPs, CRMs, etc.). The entity registry, query engine, and import validation pipeline are the hard parts -- once those are solved, adding a new entity is just defining its fields. With AI coding tools, that takes minutes.

### What's Included

- **Async job execution** -- long-running import/export jobs with background workers and status tracking
- **Export filter DSL** -- safe, flexible query language with comparison, string, logical, and relative date operators
- **Presigned URL uploads** -- clients upload directly to cloud storage, bypassing API Gateway size limits
- **Cron scheduling** -- schedule recurring exports using cron expressions with APScheduler
- **Multi-tenant isolation** -- JWT authentication with JWKS, secret-key, and dev bypass modes
- **Multi-cloud storage** -- S3, Azure Blob Storage, and GCP Cloud Storage support
- **Import validation** -- per-row validation with preview before execution, custom validators per entity
- **Entity registry** -- single source of truth for field metadata, relationships, and validation rules
- **Embeddable UI** -- React micro-frontend you can drop into your host app via module federation
- **Multi-cloud Terraform** -- deploy to AWS (ECS/Fargate), GCP, or Azure

### How to Use It

The included sample entities (vendor, bill, invoice, project) are fully working reference implementations with import, export, filtering, and scheduling.

1. **Clone and deploy** -- download the source and spin up infrastructure with the included Terraform configs
2. **Point your AI tool at the codebase** -- the project includes detailed `CLAUDE.md` files that give AI tools full context
3. **Describe what you need** -- tell your AI tool to *"add a payment entity following the same patterns as bill"*
4. **Test and ship** -- run the included tests as a baseline, add entity-specific tests, and deploy

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│  API Layer  (FastAPI routers, DTOs, OpenAPI docs)     │
├──────────────────────────────────────────────────────┤
│  Auth       (JWT: JWKS / HS256 / dev bypass)          │
├──────────────────────────────────────────────────────┤
│  Services   (JobRunner, ExportExecutor, ImportValid.)  │
├──────────────────────────────────────────────────────┤
│  Domain     (Entities, enums, interfaces — no deps)   │
├──────────────────────────────────────────────────────┤
│  Entities   (Registry: field metadata, relationships) │
├──────────────────────────────────────────────────────┤
│  Infrastructure                                       │
│    DB        (SQLAlchemy repos, Alembic migrations)   │
│    Query     (Filter DSL engine, schema generation)   │
│    Storage   (S3 / Azure Blob / GCP Cloud Storage)    │
│    Queue     (SQS / Azure Queue / GCP Pub/Sub)        │
│    SaaS      (Entity handlers: fetch/create/update)   │
│    Scheduling (APScheduler cron jobs)                 │
└──────────────────────────────────────────────────────┘
```

**Key tables**: `jobs` (job definitions with cron schedules), `job_runs` (execution history with status/results), `sample_vendors` / `sample_bills` / `sample_invoices` / `sample_projects` (demo data tables).

**Export flow**: Create export request with entity + filters → query engine builds SQL from registry → results written to CSV/JSON → uploaded to cloud storage → presigned download URL returned.

**Import flow**: Client requests presigned upload URL → uploads file directly to S3/Azure/GCP → server validates format and content → optional preview with per-row validation → execute import asynchronously.

For the detailed filter DSL reference (operators, relative dates, nested fields), see [docs/EXPORT_FILTER_DSL.md](docs/EXPORT_FILTER_DSL.md).

## Deployment Guide

### Prerequisites

- Cloud CLI configured: AWS CLI, `gcloud`, or `az` (depending on your cloud)
- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.5
- [Docker](https://docs.docker.com/get-docker/)
- PostgreSQL 15+ (provisioned automatically by shared-infrastructure)

### Step 1: Deploy shared-infrastructure

The [shared-infrastructure](https://github.com/saasdog-ai/shared-infrastructure) project creates the foundational resources (VPC, ECS cluster, RDS PostgreSQL) that this service runs on. If you've already deployed it for integration-platform, skip to Step 2.

```bash
git clone https://github.com/saasdog-ai/shared-infrastructure.git
cd shared-infrastructure
```

**Bootstrap the Terraform state backend** (one-time):

```bash
cd infra/aws/terraform/bootstrap
terraform init
terraform apply -var="company_prefix=mycompany"
```

**Deploy the infrastructure**:

```bash
cd ../  # back to infra/aws/terraform/
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars: set company_prefix, environment, region, RDS settings
```

```bash
terraform init \
  -backend-config="bucket=mycompany-shared-infra-tfstate-dev" \
  -backend-config="key=terraform.tfstate" \
  -backend-config="region=us-east-1" \
  -backend-config="dynamodb_table=mycompany-shared-infra-tflock-dev" \
  -backend-config="encrypt=true"

terraform apply
```

**Save the outputs** — you'll paste them into the next step's `terraform.tfvars`:

```bash
terraform output
```

| shared-infrastructure output | import-export-orchestrator variable |
|------------------------------|-------------------------------------|
| `vpc_id` | `shared_vpc_id` |
| `public_subnet_ids` | `shared_public_subnet_ids` |
| `private_subnet_ids` | `shared_private_subnet_ids` |
| `ecs_cluster_arn` | `shared_ecs_cluster_arn` |
| `ecs_cluster_name` | `shared_ecs_cluster_name` |
| `rds_endpoint` | `shared_rds_endpoint` |
| `rds_address` | `shared_rds_address` |
| `rds_security_group_id` | `shared_rds_security_group_id` |
| `rds_master_password_secret_arn` | `shared_rds_master_password_secret_arn` |

### Step 2: Deploy import-export-orchestrator

```bash
git clone https://github.com/saasdog-ai/import-export-orchestrator.git
cd import-export-orchestrator
```

**Bootstrap the state backend** (one-time):

```bash
cd infra/aws/terraform/bootstrap
terraform init && terraform apply
```

**Configure and deploy**:

```bash
cd ../  # back to infra/aws/terraform/
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars: paste shared-infrastructure outputs using the mapping above
```

```bash
terraform init \
  -backend-config="bucket=import-export-terraform-state-dev-ACCOUNT_ID" \
  -backend-config="key=terraform.tfstate" \
  -backend-config="region=us-east-1" \
  -backend-config="encrypt=true" \
  -backend-config="dynamodb_table=import-export-terraform-state-lock-dev"

terraform apply
```

### Step 3: Initialize the database

The container's `start.sh` runs Alembic migrations on first boot, but the database and application user must be created first.

**Option A: Use RDS master credentials** (simpler, default for dev). Terraform's `secrets.tf` auto-generates a password and constructs `DATABASE_URL` using the RDS master credentials. The `start.sh` script creates the database automatically.

**Option B: Create a dedicated application user** (recommended for production):

```bash
psql -h <rds-endpoint> -U postgres -f scripts/init-database.sql
```

This creates the `job_runner` database and a `job_runner` user with appropriate permissions. Then update the `DATABASE_URL` secret in Secrets Manager with the new credentials.

### Step 4: Set up secrets

| Secret | Purpose | How to Create |
|--------|---------|---------------|
| `DATABASE_URL` | PostgreSQL connection | Auto-constructed by Terraform from shared-infra outputs |
| `JWT_SECRET_KEY` | Signs JWT tokens (HS256 mode) | `openssl rand -base64 48` |
| `JWT_JWKS_URL` | JWKS endpoint (RS256 mode) | URL from your auth provider |
| `CLOUD_STORAGE_BUCKET` | S3/Azure/GCP bucket for files | Created by Terraform (`storage.tf`) |
| `MESSAGE_QUEUE_NAME` | SQS/Azure Queue/Pub/Sub | Created by Terraform (`queue.tf`) |

**Where to store them**:
- **AWS**: Secrets Manager (Terraform creates the `DATABASE_URL` secret in `infra/aws/terraform/secrets.tf`)
- **GCP**: Secret Manager
- **Azure**: Key Vault
- **Local dev**: `.env` file (gitignored)

### Step 5: Verify deployment

```bash
curl https://your-app-url/health
# {"status": "healthy"}

curl https://your-app-url/health/db
# {"status": "healthy", "database": "connected"}

curl https://your-app-url/docs
# Swagger UI — interactive API documentation
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `APP_ENV` | Environment (`development` / `production`) | `development` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `AUTH_ENABLED` | Enable JWT authentication | `false` |
| `JWT_ALGORITHM` | JWT algorithm (`RS256`, `ES256`, `HS256`) | `RS256` |
| `JWT_JWKS_URL` | JWKS endpoint for public keys | - |
| `JWT_SECRET_KEY` | Secret for HS256 algorithm | `CHANGE_THIS_IN_PRODUCTION` |
| `JWT_ISSUER` | Expected token issuer | - |
| `JWT_AUDIENCE` | Expected token audience | - |
| `JWT_CLIENT_ID_CLAIM` | Claim containing client ID | `client_id` |
| `CLOUD_PROVIDER` | Cloud provider (`aws` / `azure` / `gcp`) | - |
| `CLOUD_STORAGE_BUCKET` | Bucket name for file storage | - |
| `MESSAGE_QUEUE_NAME` | Queue name for async jobs | - |
| `SCHEDULER_ENABLED` | Enable cron job scheduling | `true` |
| `JOB_RUNNER_MAX_WORKERS` | Max concurrent job workers | `5` |
| `EXPORT_FILE_FORMAT` | Default export format (`csv` / `json`) | `csv` |
| `PRESIGNED_URL_EXPIRATION` | Upload URL expiration (seconds) | `3600` |
| `ALLOWED_ORIGINS` | CORS allowed origins (JSON array) | `["http://localhost:3000", "http://localhost:5173"]` |

> **Production validation**: When `APP_ENV=production`, the app enforces that `AUTH_ENABLED=true`, JWT is properly configured, `MESSAGE_QUEUE_NAME` is set, cloud storage is configured, and CORS origins are explicit. It will refuse to start otherwise.

## Customization Guide

### Connect to Your Own Data (Replace Entity Handlers)

This is the most important customization. The included entity handlers (`app/infrastructure/saas/handlers/`) read and write demo `sample_*` tables. In production, you replace them with access to your actual business data.

**What handlers do**: Each entity has a handler that implements the `EntityHandler` protocol — `fetch()`, `find_existing()`, `create()`, `update()`, `delete()`, `build_query()`, `get_column()`, and `get_required_fields()`.

**EntityHandler protocol** (from `app/infrastructure/saas/base.py`):

```python
class EntityHandler(Protocol):
    async def fetch(self, session: AsyncSession, client_id: UUID) -> list[dict]
    async def find_existing(self, session, client_id, match_key, match_value) -> Model | None
    async def create(self, session, record: dict, client_id: UUID) -> dict  # {"action": "created"}
    async def update(self, session, existing, record: dict) -> dict  # {"action": "updated"}
    async def delete(self, session, existing) -> dict  # {"action": "deleted"}
    def get_required_fields(self) -> list[str]
    def build_query(self, client_id: UUID) -> Select
    def get_column(self, field_path: str) -> Column | None
```

**Two approaches**:

1. **Direct DB access** (current pattern): Replace the SQLAlchemy queries in each handler to point at your own tables instead of `sample_*`. Simplest if your data lives in the same PostgreSQL instance. See `app/infrastructure/saas/handlers/vendor.py` for the simplest example.

2. **API client**: Replace the handler implementations with HTTP calls to your system's REST API. The services layer only depends on the `EntityHandler` protocol — the implementation can be anything.

Handlers are registered in `MockSaaSApiClient.__init__` (`app/infrastructure/saas/client.py`).

### Add a New Entity

Adding a new entity (e.g., "payment") requires **2 new files** + **1 enum entry** + **DB model** + **migration** + **handler registration**:

1. **Entity definition** — create `app/entities/payment.py`:

```python
from app.entities._registry import EntityDefinition, FieldDef, RelationshipDef, registry

payment = EntityDefinition(
    name="payment",
    label="Payments",
    description="Payment records",
    fields=[
        FieldDef(name="id", type="uuid", label="ID"),
        FieldDef(name="amount", type="number", label="Amount", required=True),
        FieldDef(name="date", type="date", label="Date", required=True),
        FieldDef(name="created_at", type="datetime", label="Created At"),
    ],
    relationships=[
        RelationshipDef(name="vendor", entity="vendor", type="many_to_one",
            foreign_key="vendor_id",
            fields=[FieldDef(name="name", type="string", label="Vendor Name")]),
    ],
    required_fields=["amount", "date"],
)
registry.register(payment)
```

2. **Import trigger** — add to `app/entities/__init__.py`:
```python
from app.entities import payment  # noqa: F401
```

3. **Enum entry** — add `PAYMENT = "payment"` to `ExportEntity` in `app/domain/entities.py`

4. **DB model** — add `SamplePaymentModel` to `app/infrastructure/db/models.py`

5. **Migration** — `make migrate msg="add sample_payments table" && make migrate-upgrade`

6. **Handler** — create `app/infrastructure/saas/handlers/payment.py` implementing the `EntityHandler` protocol, register in `MockSaaSApiClient.__init__`

**What auto-updates** after these steps:
- Schema endpoint (`GET /schema/entities`) — entity appears automatically
- Query engine fields and joins — auto-generated from registry
- Import validator required fields — auto-generated from registry
- Startup validation — checks `ExportEntity` enum matches registry

### Custom Import Validators

Entities can define custom validation functions that run during import:

```python
def validate_amount_positive(row: dict, row_num: int, errors: list[dict]) -> None:
    amount = row.get("amount")
    if amount is not None:
        try:
            if float(amount) <= 0:
                errors.append({"row": row_num, "field": "amount",
                    "message": "Amount must be greater than zero"})
        except (ValueError, TypeError):
            pass

EntityDefinition(name="payment", ..., validators=[validate_amount_positive])
```

See `app/entities/bill.py` for a complete example with amount and due date validation.

### Enable JWT Authentication

By default, auth is disabled (`AUTH_ENABLED=false`). All requests use a default client ID during development.

**To enable in production**:

1. Set `AUTH_ENABLED=true`
2. Choose an approach:
   - **RS256/ES256 (JWKS)** — recommended: Set `JWT_JWKS_URL=https://your-auth-server/.well-known/jwks.json`, and optionally `JWT_ISSUER` and `JWT_AUDIENCE`. The backend fetches and caches public keys automatically.
   - **HS256 (shared secret)**: Set `JWT_ALGORITHM=HS256` and `JWT_SECRET_KEY` to a strong random value. Your auth server signs tokens with the same secret.
3. The platform extracts `client_id` from the JWT payload (configurable via `JWT_CLIENT_ID_CLAIM`, falls back to `sub`).

**Required token claims** (minimum):

```json
{
  "client_id": "uuid-string",
  "exp": 1234567890,
  "iat": 1234567890
}
```

The auth backend is in `app/auth/backend.py` (uses `python-jose`). JWKS caching is in `app/auth/jwks.py`.

### Storage Adapters

File storage is pluggable via `CloudStorageInterface` (`app/infrastructure/storage/interface.py`):

| Provider | Backend | Config |
|----------|---------|--------|
| AWS | S3 | Set `CLOUD_PROVIDER=aws`, `CLOUD_STORAGE_BUCKET` |
| Azure | Blob Storage | Set `CLOUD_PROVIDER=azure`, `CLOUD_STORAGE_BUCKET`, `AZURE_STORAGE_ACCOUNT_NAME` |
| GCP | Cloud Storage | Set `CLOUD_PROVIDER=gcp`, `CLOUD_STORAGE_BUCKET` |
| Local | Filesystem | Default when no cloud provider is set (files in `/tmp/exports`) |

Terraform creates the S3 bucket with versioning, encryption, CORS (for presigned uploads), and lifecycle rules (Glacier after 90 days, delete after 365 days).

### Queue Adapters

Job queuing is pluggable via `MessageQueueInterface` (`app/infrastructure/queue/interface.py`):

| Provider | Backend | Config |
|----------|---------|--------|
| AWS | SQS | Set `MESSAGE_QUEUE_NAME` (created by Terraform) |
| Azure | Azure Queue | Set `CLOUD_PROVIDER=azure`, `MESSAGE_QUEUE_NAME` |
| GCP | Pub/Sub | Set `CLOUD_PROVIDER=gcp`, `MESSAGE_QUEUE_NAME` |
| Local | In-memory | Default when no queue is configured |

## Quick Start (Local Dev)

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL 15+ (if running without Docker)

### With Docker

```bash
git clone <repository-url>
cd import-export-orchestrator
cp .env.example .env
make docker-up
```

This starts PostgreSQL (port 5433), the app (port 8000), and runs migrations automatically.

**Access**:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Health: http://localhost:8000/health

```bash
make docker-down  # Stop services
```

### Without Docker

```bash
python -m venv .venv
source .venv/bin/activate
make install-dev
cp .env.example .env
# Edit .env with your database connection
make migrate-upgrade
make run
```

### Micro-Frontend UI

```bash
cd ui
npm install
npm run build && npm run preview  # Runs on :3000
```

The micro-frontend **must** run in `preview` mode (not `dev`) — `vite-plugin-federation` requires built assets for `remoteEntry.js`.

The [saas-host-app](https://github.com/saasdog-ai/saas-host-app) loads this micro-frontend and proxies API calls to the backend.

## API Reference

All endpoints require a Bearer JWT token (production) or use a default client ID (development).

Interactive documentation is available at `/docs` (Swagger UI) and `/redoc` (ReDoc) when the server is running.

### Endpoints Summary

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/health/db` | Database connectivity check |
| **Jobs** | | |
| `POST` | `/jobs` | Create a job definition (with optional cron schedule) |
| `GET` | `/jobs` | List all jobs for authenticated client |
| `GET` | `/jobs/{id}` | Get job definition |
| `PUT` | `/jobs/{id}` | Update job definition |
| `POST` | `/jobs/{id}/run` | Manually trigger a job run |
| `GET` | `/jobs/{id}/runs` | List runs for a job (supports date filtering) |
| `GET` | `/jobs/{id}/runs/{run_id}` | Get specific run details |
| **Exports** | | |
| `POST` | `/exports` | Create and trigger an export |
| `POST` | `/exports/preview` | Preview export results without creating a job |
| `GET` | `/exports/{run_id}/result` | Get export result metadata |
| `GET` | `/exports/{run_id}/download` | Get presigned download URL |
| `GET` | `/exports/{run_id}/file` | Download export file directly |
| **Imports** | | |
| `POST` | `/imports/request-upload` | Get presigned URL for direct file upload |
| `POST` | `/imports/confirm-upload` | Validate uploaded file, get column metadata |
| `POST` | `/imports/preview` | Preview import with per-row validation |
| `POST` | `/imports/execute` | Execute the import (CREATE/UPDATE/UPSERT/DELETE) |
| **Schema** | | |
| `GET` | `/schema/entities` | List all registered entities with field metadata |

### Presigned URL Import Flow

Imports use presigned URLs so clients upload files directly to cloud storage, bypassing API Gateway size limits:

1. **Request upload URL**: `POST /imports/request-upload` with `{filename, entity, content_type}` — returns presigned PUT URL and `file_key`
2. **Upload directly**: Client PUTs file to the presigned URL (goes directly to S3/Azure/GCP)
3. **Confirm & validate**: `POST /imports/confirm-upload` with `{file_key, entity}` — server validates, returns column info
4. **Preview** (optional): `POST /imports/preview` — returns per-row validation results
5. **Execute**: `POST /imports/execute` — runs the import asynchronously

Tenant isolation is enforced via file key prefix (`imports/{client_id}/...`).

### Export Filter Example

```json
{
  "entity": "bill",
  "fields": ["id", "amount", "date", "vendor.name"],
  "filters": {
    "operator": "and",
    "filters": [
      {"field": "amount", "operator": "gt", "value": 1000},
      {"field": "created_at", "operator": "gte", "value": "relative:last_30_days"}
    ]
  },
  "limit": 100
}
```

Supports: comparison operators (`eq`, `gt`, `between`, etc.), string operators (`contains`, `ilike`), logical operators (`and`, `or`, `not`), nested fields (`vendor.name`), and relative dates (`relative:last_30_days`). See [docs/EXPORT_FILTER_DSL.md](docs/EXPORT_FILTER_DSL.md) for the full reference.

### OpenAPI / Client SDK Generation

```bash
curl http://localhost:8000/openapi.json -o openapi.json

npx @openapitools/openapi-generator-cli generate -i openapi.json -g typescript-fetch -o ./clients/typescript
```

See [docs/OPENAPI_CLIENT_GENERATION.md](docs/OPENAPI_CLIENT_GENERATION.md) for all supported languages.

## Development

### Running Tests

```bash
# Run all tests with coverage
make test

# Run specific test file
pytest tests/unit/test_domain.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Run linter
make lint

# Format code
make format

# Type checking
make mypy

# Run all checks
make check  # lint + format + mypy + tests
```

### Database Migrations

```bash
# Create a new migration
make migrate msg="add_new_field"

# Apply migrations
make migrate-upgrade

# Rollback last migration
make migrate-downgrade
```

### CI/CD

The project includes GitHub Actions workflows for:
- **CI**: Automated testing, linting, and type checking on every push
- **Deploy**: Automated deployment to AWS using OIDC (no stored credentials)

## Technology Stack

- **Python 3.11+** / **FastAPI** - Async web framework
- **Pydantic v2** - Data validation and settings
- **SQLAlchemy 2** - Async ORM
- **Alembic** - Database migrations
- **APScheduler** - Cron job scheduling
- **PostgreSQL 15+** - Primary database
- **React / TypeScript / Vite** - Micro-frontend UI
- **pytest** - Testing with >=75% coverage
- **mypy, Ruff, Black** - Code quality
- **Docker & Docker Compose** - Containerization
- **Terraform** - Multi-cloud infrastructure (AWS, GCP, Azure)

## Project Structure

```
import-export-orchestrator/
├── app/
│   ├── api/                  # FastAPI routers and DTOs
│   ├── auth/                 # JWT authentication (JWKS + secret-key modes)
│   ├── core/                 # Configuration, DI, logging, constants
│   ├── domain/               # Domain entities and business logic
│   ├── entities/             # Entity registry (field metadata, relationships)
│   ├── infrastructure/
│   │   ├── db/               # SQLAlchemy models, repositories, migrations
│   │   ├── query/            # Query engine and schema generation
│   │   ├── queue/            # SQS, Azure Queue, GCP Pub/Sub adapters
│   │   ├── storage/          # S3, Azure Blob, GCP Cloud Storage adapters
│   │   ├── saas/             # Entity handlers (fetch, create, update, delete)
│   │   └── scheduling/       # APScheduler integration
│   ├── services/             # Business logic services
│   └── main.py               # FastAPI app entry point
├── ui/                       # React micro-frontend (Vite, TypeScript)
├── infra/
│   ├── aws/terraform/        # AWS infrastructure (ECS/Fargate, S3, SQS, ALB)
│   ├── azure/                # Azure infrastructure
│   └── gcp/                  # GCP infrastructure
├── docs/                     # Detailed documentation
├── tests/                    # Test suite (unit + integration)
├── test-data/                # Sample CSV files for import testing
├── alembic/                  # Database migrations
├── scripts/                  # Database init, seed data, deployment helpers
└── docker-compose.yml        # Local development setup
```

## Related Projects

- **[shared-infrastructure](https://github.com/saasdog-ai/shared-infrastructure)** -- Shared AWS/GCP/Azure infra (VPC, compute, database) -- deploy this first
- **[integration-platform](https://github.com/saasdog-ai/integration-platform)** -- Sister project for real-time API integrations (ERPs, CRMs) -- shares PostgreSQL
- **[saas-host-app](https://github.com/saasdog-ai/saas-host-app)** -- User-facing host app that embeds this project's micro-frontend
