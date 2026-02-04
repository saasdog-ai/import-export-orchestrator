# Import-Export Orchestrator

A production-ready backend job runner service for asynchronous import/export operations with scheduling, filtering, and cloud deployment support.

## Features

- **Async Job Execution**: Run long-running import/export jobs asynchronously with background workers
- **Configurable Exports**: Safe and flexible filter/query DSL for filtering exported data
- **Cron Scheduling**: Schedule jobs using cron expressions with APScheduler
- **REST API**: Comprehensive REST API for job management and monitoring
- **Database Tracking**: Track job status and history in PostgreSQL
- **Presigned URL Uploads**: Import files upload directly to cloud storage via presigned URLs, bypassing API Gateway size limits
- **JWT Authentication**: Multi-tenant isolation via JWT with JWKS, secret-key, and dev bypass modes
- **Multi-Cloud Storage**: S3, Azure Blob Storage, and GCP Cloud Storage support for file storage
- **Containerized**: Fully containerized with Docker and Docker Compose
- **Clean Architecture**: Hexagonal architecture with strong abstractions

## Technology Stack

- **Python 3.11+**
- **FastAPI** - Modern, fast web framework
- **Pydantic v2** - Data validation
- **SQLAlchemy 2** - ORM with async support
- **Alembic** - Database migrations
- **APScheduler** - Cron job scheduling
- **pytest** - Testing with >=75% coverage
- **mypy, Ruff, Black** - Code quality tools
- **Docker & Docker Compose** - Containerization
- **Terraform** - Infrastructure as Code

## Project Structure

```
import-export-orchestrator/
├── app/
│   ├── api/              # FastAPI routers and DTOs
│   ├── auth/             # JWT authentication (JWKS + secret-key modes)
│   ├── core/             # Configuration, DI, logging, constants
│   ├── domain/           # Domain entities and business logic
│   ├── entities/         # Entity registry (field metadata, relationships)
│   ├── infrastructure/
│   │   ├── db/           # SQLAlchemy models, repositories, migrations
│   │   ├── query/        # Query engine and schema generation
│   │   ├── queue/        # SQS, Azure Queue, GCP Pub/Sub adapters
│   │   ├── storage/      # S3, Azure Blob, GCP Cloud Storage adapters
│   │   ├── saas/         # SaaS API client and entity handlers
│   │   └── scheduling/   # APScheduler integration
│   ├── services/         # Business logic services
│   └── main.py           # FastAPI application entry point
├── ui/                   # React frontend (Vite + TypeScript + Tailwind)
├── infra/
│   ├── aws/terraform/    # AWS infrastructure (ECS/Fargate)
│   ├── azure/            # Azure infrastructure
│   └── gcp/              # GCP infrastructure
├── tests/                # Test suite (unit + integration)
├── test-data/            # Sample CSV files for import testing
├── alembic/              # Database migrations
└── docker-compose.yml    # Local development setup
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL 15+ (if running locally without Docker)

### Local Development with Docker

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd import-export-orchestrator
   ```

2. **Copy environment file**:
   ```bash
   cp .env.example .env
   ```

3. **Start services**:
   ```bash
   make docker-up
   ```

   This will:
   - Start PostgreSQL database
   - Build and start the application
   - Run database migrations automatically

4. **Access the API**:
   - API: http://localhost:8000
   - API Docs (Swagger UI): http://localhost:8000/docs
   - API Docs (ReDoc): http://localhost:8000/redoc
   - OpenAPI JSON Spec: http://localhost:8000/openapi.json
   - Health Check: http://localhost:8000/health

5. **Stop services**:
   ```bash
   make docker-down
   ```

### Local Development without Docker

1. **Create virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   make install-dev
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your database connection
   ```

4. **Run database migrations**:
   ```bash
   make migrate-upgrade
   ```

5. **Run the application**:
   ```bash
   make run
   ```

## API Endpoints

### Health Checks

- `GET /health` - Basic health check
- `GET /health/db` - Database connectivity check

### Job Management

- `POST /jobs` - Create a new job definition
- `GET /jobs/{job_id}` - Get job definition by ID
- `PUT /jobs/{job_id}` - Update job definition
- `POST /jobs/{job_id}/run` - Manually trigger a job run
- `GET /jobs/{job_id}/runs` - Get all runs for a job (supports date filtering)
- `GET /jobs/{job_id}/runs/{run_id}` - Get specific job run
- `GET /jobs` - Get all jobs for authenticated client (supports date filtering)

**Date Filtering**: Both `GET /jobs/{job_id}/runs` and `GET /jobs` support optional query parameters:
- `start_date` - Filter records created after this date/time (ISO 8601 format)
- `end_date` - Filter records created before this date/time (ISO 8601 format)

Example: `GET /jobs/{job_id}/runs?start_date=2024-01-01T00:00:00Z&end_date=2024-12-31T23:59:59Z`

See [docs/DATE_FILTERING.md](docs/DATE_FILTERING.md) for detailed documentation.

### Export Operations

- `POST /exports` - Create and trigger an export job
- `POST /exports/preview` - Preview export results (returns data without creating a job)
- `GET /exports/{run_id}/result` - Get export result for a completed run
- `GET /exports/{run_id}/download` - Get pre-signed download URL
- `GET /exports/{run_id}/file` - Download export file directly

### Import Operations

- `POST /imports/request-upload` - Get a presigned URL for direct file upload to cloud storage
- `POST /imports/confirm-upload` - Validate an uploaded file and get column metadata
- `POST /imports/preview` - Preview import changes with per-row validation before execution
- `POST /imports/execute` - Execute the import (CREATE, UPDATE, UPSERT, or DELETE)

#### Presigned URL Upload Flow

Imports use a presigned URL flow so clients upload files directly to cloud storage, bypassing API Gateway size limits:

1. **Request upload URL**: `POST /imports/request-upload` with `{filename, entity, content_type}` — returns a presigned PUT URL and a `file_key`
2. **Upload directly**: Client PUTs the file to the presigned URL (goes directly to S3/Azure/GCP, no API Gateway involved)
3. **Confirm & validate**: `POST /imports/confirm-upload` with `{file_key, entity}` — server downloads from cloud, validates format and content, returns column info for the mapping UI
4. **Preview** (optional): `POST /imports/preview` with `{file_path, entity}` — returns per-row validation results
5. **Execute**: `POST /imports/execute` with `{file_path, entity}` — runs the import job asynchronously

Tenant isolation is enforced via file key prefix (`imports/{client_id}/...`). The server rejects requests where the `file_key` doesn't match the authenticated client.

See the interactive API documentation at `/docs` for detailed request/response schemas.

> **Note**: Client isolation is handled via JWT `client_id` claim, not URL path parameters.

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

## AWS Deployment

### Prerequisites

- Terraform >= 1.0
- AWS CLI configured
- AWS account with appropriate permissions

### Quick Start

1. **Navigate to Terraform directory**:
   ```bash
   cd infra/aws/terraform
   ```

2. **Copy example variables**:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

3. **Edit terraform.tfvars** with your values

4. **Set database password** (never commit this):
   ```bash
   export TF_VAR_database_password="your-secure-password"
   ```

5. **Initialize Terraform**:
   ```bash
   terraform init
   ```

6. **Plan deployment**:
   ```bash
   terraform plan -var-file="terraform.tfvars"
   ```

7. **Apply configuration**:
   ```bash
   terraform apply -var-file="terraform.tfvars"
   ```

See `infra/aws/terraform/README.md` for detailed instructions.

### GitHub Actions CI/CD

The project includes GitHub Actions workflows for:

- **CI**: Automated testing, linting, and type checking
- **Deploy**: Automated deployment to AWS using OIDC (no stored credentials)

Configure the following secrets in GitHub:

- `AWS_ROLE_ARN` - ARN of IAM role for GitHub Actions OIDC
- `DATABASE_PASSWORD` - Database password (or use AWS Secrets Manager)

## Security

### Authentication

The project includes a JWT authentication module (`app/auth/`) supporting:

- **JWKS mode** (RS256/ES256): Fetches public keys from a JWKS endpoint for token verification
- **Secret key mode** (HS256): Uses a shared secret for token signing/verification
- **Dev mode**: When `AUTH_ENABLED=false` (default), all requests use a default client ID (`00000000-0000-0000-0000-000000000000`)

To enable authentication in production, set `AUTH_ENABLED=true` and configure the JWT settings in `.env` (see `.env.example`).

### Secrets Management

**Never commit secrets to the repository!**

- Use `.env` files locally (gitignored)
- Use AWS Secrets Manager / Azure Key Vault / GCP Secret Manager in production
- Use environment variables for Docker/Terraform
- Use IAM roles / Service Accounts for cloud authentication

See `.gitignore` for excluded files.

## Architecture

### Clean Architecture

The project follows hexagonal (clean) architecture principles:

- **Domain Layer** (`app/domain/`): Core business entities and logic
- **Services Layer** (`app/services/`): Business logic orchestration
- **Infrastructure Layer** (`app/infrastructure/`): External concerns (DB, scheduling, SaaS APIs)
- **API Layer** (`app/api/`): HTTP endpoints and DTOs
- **Core Layer** (`app/core/`): Configuration, dependency injection, logging

### Database Abstraction

The database layer is designed to be swappable:

- Repository pattern with interfaces
- SQLAlchemy models in `infrastructure/db/models.py`
- Repository implementations in `infrastructure/db/repositories.py`

To swap databases, implement new repository classes following the same interface.

### Export Filter DSL

The export filter DSL supports:

- **Comparison operators**: `eq`, `ne`, `lt`, `lte`, `gt`, `gte`, `in`, `between`
- **String operators**: `contains`, `startswith`, `endswith`, `ilike`
- **Logical operators**: `and`, `or`, `not`
- **Nested fields**: `vendor.name`, `project.code`
- **Relative dates**: `relative:last_7_days`, `relative:last_30_days`, `relative:last_90_days`, `relative:this_month`, `relative:last_month`, `relative:this_quarter`, `relative:this_year`

Example:
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

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests (maintain >=75% coverage)
5. Run linting and type checking
6. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions, please open a GitHub issue.

