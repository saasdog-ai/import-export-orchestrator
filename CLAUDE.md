# CLAUDE.md — Import/Export Orchestrator

## Project Overview

A FastAPI backend for managing asynchronous import/export operations with scheduling, cloud storage, and multi-tenant isolation via JWT.

**Stack:** Python 3.11+, FastAPI, SQLAlchemy 2, Pydantic v2, Alembic, APScheduler, Terraform (AWS)

**Architecture:** Clean Architecture layers:
- `app/api/` — FastAPI routers and DTOs
- `app/domain/` — Entities, enums, interfaces (no framework deps)
- `app/services/` — Business logic orchestration
- `app/infrastructure/` — DB, queue, storage, SaaS client adapters
- `app/entities/` — Entity registry (single source of truth for field metadata)
- `app/auth/` — JWT authentication (JWKS and secret-key modes)

## Entity Onboarding

To add a new entity (e.g., "payment"), create **2 files** + add **1 enum entry** + **DB model** + **migration** + **register handler**:

### Step 1: Entity Definition
Create `app/entities/payment.py`:
```python
from app.entities._registry import EntityDefinition, FieldDef, RelationshipDef, registry

payment = EntityDefinition(
    name="payment",
    label="Payments",
    description="Payment records",
    fields=[
        FieldDef(name="id", type="uuid", label="ID"),
        FieldDef(name="external_id", type="string", label="External ID"),
        FieldDef(name="amount", type="number", label="Amount", required=True),
        FieldDef(name="date", type="date", label="Date", required=True),
        FieldDef(name="created_at", type="datetime", label="Created At"),
        FieldDef(name="updated_at", type="datetime", label="Updated At"),
    ],
    relationships=[
        RelationshipDef(
            name="vendor",
            entity="vendor",
            type="many_to_one",
            foreign_key="vendor_id",
            fields=[
                FieldDef(name="id", type="uuid", label="Vendor ID"),
                FieldDef(name="name", type="string", label="Vendor Name"),
            ],
        ),
    ],
    required_fields=["amount", "date"],
    date_fields={"date", "paid_on_date"},
    decimal_fields={"amount"},
)

registry.register(payment)
```

### Step 2: Import trigger
Add to `app/entities/__init__.py`:
```python
from app.entities import payment  # noqa: F401
```

### Step 3: Enum entry
Add to `app/domain/entities.py` `ExportEntity`:
```python
PAYMENT = "payment"
```

### Step 4: DB model
Add `SamplePaymentModel` to `app/infrastructure/db/models.py` following existing patterns.

### Step 5: Migration
```bash
make migrate msg="add sample_payments table"
make migrate-upgrade
```

### Step 6: Handler
Create `app/infrastructure/saas/handlers/payment.py` implementing `fetch`, `find_existing`, `create`, `update`, `delete`, and `get_required_fields`. Register it in `MockSaaSApiClient.__init__`.

**What auto-updates:**
- Schema endpoint (`GET /schema/entities`) — entity appears automatically
- Query engine fields/joins — auto-generated from registry
- Import validator required fields — auto-generated from registry
- Startup validation — checks ExportEntity enum matches registry

## Entity Definition Patterns

### Simple entity (no joins)
```python
EntityDefinition(name="vendor", label="Vendors", description="...",
    fields=[...], required_fields=["name"])
```

### Entity with joins
```python
EntityDefinition(name="bill", ...,
    relationships=[
        RelationshipDef(name="vendor", entity="vendor", type="many_to_one",
            foreign_key="vendor_id",
            fields=[FieldDef(name="name", type="string", label="Vendor Name")])
    ])
```

### Field name mapping
For entities where DB column names differ from schema names (e.g., `total_amount` -> `amount`), mapping is handled in `app/infrastructure/saas/utils.py:model_to_dict()`.

## Handler Patterns

### DB-direct mock handler
All current handlers query the SQLAlchemy ORM directly. See `app/infrastructure/saas/handlers/vendor.py` for the simplest example.

### Fetch with nested data
`bill.py` and `invoice.py` handlers fetch parent records then sub-query related entities to build nested dicts. The query engine uses these nested dicts for join-based exports.

### Required: `fetch()` must return nested dicts
If entity X has a relationship to entity Y (e.g., bill -> vendor), the `fetch()` method **must** return records with nested dicts like:
```python
{"id": "...", "amount": 100, "vendor": {"id": "...", "name": "Acme"}}
```
The query engine resolves `vendor.name` by looking up `record["vendor"]["name"]`.

## Import Flow (Presigned URL Upload)

The import flow uses presigned URLs so clients upload files directly to cloud storage, bypassing API Gateway size limits:

1. **`POST /imports/request-upload`** — Client sends `{filename, entity, content_type}`. Server validates, generates an S3/Azure/GCP presigned PUT URL, returns `{upload_url, file_key, expires_in}`.
2. **Client uploads directly** — Client PUTs the file to the presigned URL (bypasses API Gateway entirely).
3. **`POST /imports/confirm-upload`** — Client sends `{file_key, entity}`. Server downloads from cloud, validates file format and content, returns `{columns, file_path, entity, filename}`. Enforces tenant isolation via file key prefix.
4. **`POST /imports/preview`** — (Optional) Preview all records with per-row validation status before executing.
5. **`POST /imports/execute`** — Execute the import using `{file_path, entity}` from confirm-upload.

### Key design decisions
- Files are downloaded to `/tmp` for validation because `ImportValidator` operates on local file paths
- Temp files are cleaned up in `finally` blocks after processing (both import and export paths)
- Tenant isolation: `file_key` must match `imports/{client_id}/...` — server rejects mismatched keys with 403
- Allowed upload types: `text/csv`, `application/json` (defined in `app/core/constants.py`)
- The old `POST /imports/upload` multipart endpoint has been removed

### Storage interface methods for presigned uploads
- `CloudStorageInterface.generate_presigned_upload_url()` — S3 `put_object`, Azure SAS with write permissions, GCP signed URL with PUT
- `CloudStorageInterface.file_exists()` — S3 `head_object`, Azure `get_blob_properties`, GCP `blob.exists()`

### Temp file lifecycle
- **Export with cloud storage**: generate locally → upload to cloud → delete local file
- **Export without cloud storage** (dev): file stays in `/tmp` for download via `/exports/{run_id}/file`
- **Import from cloud storage**: download to `/tmp` → validate/process → delete local file in `finally`
- **Import from local file** (dev): use file directly, no temp file created

## Datetime Convention

All datetimes are **naive UTC** throughout the codebase. Never use timezone-aware datetimes.

- **DB columns**: `TIMESTAMP WITHOUT TIME ZONE` — defaults use `datetime.now(UTC).replace(tzinfo=None)`
- **Query engine**: `resolve_relative_date()` returns naive UTC — `datetime.now(UTC).replace(tzinfo=None)`
- **Serialization**: `model_to_dict()` appends `"Z"` suffix to ISO strings for API responses
- **Parsing**: `parse_date()` strips tzinfo from any timezone-aware input via `.astimezone(UTC).replace(tzinfo=None)`
- **In-memory filters**: ISO strings with `"Z"` are parsed and stripped to naive UTC before comparison

**Why**: asyncpg rejects comparisons between timezone-aware parameters and `TIMESTAMP WITHOUT TIME ZONE` columns. Keeping everything naive UTC avoids this mismatch.

## Infrastructure Deployment

### AWS
Terraform configs in `infra/aws/terraform/`. Key files:
- `variables.tf` — all configurable values
- `ecs.tf` — Fargate task definition with env vars
- `rds.tf` — PostgreSQL database
- `alb.tf` — Load balancer (with optional HTTPS)
- `storage.tf` — S3 bucket with versioning, encryption, CORS (for presigned uploads), and lifecycle rules
- `secrets.tf` — Secrets Manager for DB password

### Deploy
```bash
cd infra/aws/terraform
terraform init -backend-config="..."
terraform plan
terraform apply
```

### CI/CD
`.github/workflows/deploy.yml` uses GitHub OIDC for keyless AWS auth. Account ID is auto-detected via `aws sts get-caller-identity`.

### Known issue: ECS deployment with `:latest` tag
The deploy workflow pushes to ECR with `:latest` tag, but Terraform doesn't detect image content changes when the tag stays the same. After a deploy, you may need to force a new ECS deployment:
```bash
aws ecs update-service --cluster import-export-orchestrator-cluster-dev \
  --service import-export-orchestrator-service-dev \
  --task-definition import-export-orchestrator-dev:<REVISION> \
  --force-new-deployment
```
Check the current task definition revision with:
```bash
aws ecs describe-services --cluster import-export-orchestrator-cluster-dev \
  --services import-export-orchestrator-service-dev \
  --query 'services[0].deployments[*].{status:status,taskDef:taskDefinition,running:runningCount}'
```

## Testing Patterns

### Run all checks
```bash
make check    # lint + format + mypy + tests
make test     # tests only
```

### Test structure
- `tests/unit/` — unit tests
- `tests/mocks/` — shared mock objects
- `tests/conftest.py` — fixtures (mock DB, test client, sample data)

### Adding tests for a new entity
Add tests to `tests/unit/test_entity_registry.py` verifying fields/joins match, and `tests/unit/test_entity_handlers.py` verifying handler methods.

## What NOT to Modify

These generic services work for any entity — do not add entity-specific logic to them:
- `app/services/job_runner.py` — orchestrates job execution
- `app/infrastructure/query/engine.py` — builds SQL queries from filter DSL
- `app/services/import_validator.py` — validates import files
- `app/infrastructure/query/schema.py` — auto-generated from registry
- `app/api/schema.py` — auto-generated from registry
