# Infrastructure Onboarding Guide

This guide covers deploying the Import/Export Orchestrator to cloud infrastructure. It consolidates deployment steps, security hardening, and production configuration.

## Customer Deployment Checklist

Before deploying, gather the following values:

| Value | Required | Where Used |
|-------|----------|------------|
| AWS region | Yes | All resources |
| Environment name (dev/staging/prod) | Yes | Resource naming |
| Database password | Yes | RDS, ECS task |
| GitHub repository (owner/repo) | Yes | OIDC CI/CD |
| Container image URI | Yes | ECS task definition |
| ACM certificate ARN | No | HTTPS on ALB |
| Allowed CORS origins | No | API CORS headers |
| VPC CIDR | No | Networking (default: 10.0.0.0/16) |

## AWS Deployment

### Architecture

- **ECS Fargate** — Container orchestration (no servers to manage)
- **RDS PostgreSQL** — Managed database
- **S3** — Export file storage
- **SQS** — Message queue for async job processing
- **ALB** — Application Load Balancer (optional, supports HTTPS)
- **Secrets Manager** — Database password storage
- **ECR** — Container image registry

### Step 1: Prerequisites

- AWS CLI installed and configured (`aws configure`)
- Terraform >= 1.0 installed
- Docker installed (for building container images)
- GitHub repository with Actions enabled

### Step 2: Bootstrap State Backend (One Time)

```bash
cd infra/aws/terraform/bootstrap
terraform init
terraform apply
```

This creates the S3 bucket and DynamoDB table for Terraform remote state.

### Step 3: Configure Variables

```bash
cd infra/aws/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values. Key settings:

```hcl
aws_region         = "us-east-1"
environment        = "dev"
project_name       = "import-export-orchestrator"
github_repository  = "your-org/import-export-orchestrator"

# Database
database_instance_class    = "db.t3.micro"   # Production: db.t3.small or larger
database_allocated_storage = 20

# ECS
ecs_task_cpu       = 512    # Production: 1024+
ecs_task_memory    = 1024   # Production: 2048+
ecs_desired_count  = 1      # Production: 2+ for HA
enable_alb         = true

# HTTPS (optional)
acm_certificate_arn = ""  # Provide ACM cert ARN to enable HTTPS
```

### Step 4: Set Database Password

```bash
export TF_VAR_database_password="your-secure-password-here"
```

### Step 5: Initial Deployment

```bash
terraform init
terraform plan
terraform apply
```

This creates all infrastructure including the GitHub OIDC CI/CD role.

### Step 6: Configure GitHub Secrets

Get the CI/CD role ARN:

```bash
terraform output cicd_role_arn
```

Add secrets to your GitHub repository (Settings > Environments > [env] > Secrets):

- **`AWS_ROLE_ARN`**: The CI/CD role ARN from above
- **`DATABASE_PASSWORD`**: Your database password

### Step 7: Build and Push Docker Image

```bash
# Get ECR repository URL
terraform output ecr_repository_url

# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  $(terraform output -raw ecr_repository_url | sed 's|https://||')

# Build and push
docker build -t import-export-orchestrator:latest .
docker tag import-export-orchestrator:latest \
  $(terraform output -raw ecr_repository_url):latest
docker push $(terraform output -raw ecr_repository_url):latest
```

### Step 8: Ongoing Deployments

After initial bootstrap, all deployments go through GitHub Actions:

1. Push to `main` branch to auto-deploy
2. Or manually trigger: Actions > Deploy to AWS > Run workflow

### Verify Deployment

```bash
# Check ECS service status
aws ecs describe-services \
  --cluster import-export-orchestrator-cluster-dev \
  --services import-export-orchestrator-service-dev

# Check health (if ALB enabled)
curl http://$(terraform output -raw alb_dns_name)/health

# Check logs
aws logs tail /ecs/import-export-orchestrator-dev --follow
```

## Production vs Dev Configuration

| Setting | Dev Value | Production Recommendation |
|---------|-----------|--------------------------|
| `database_instance_class` | `db.t3.micro` | `db.t3.small` or larger |
| `ecs_task_cpu` | 512 | 1024+ |
| `ecs_task_memory` | 1024 | 2048+ |
| `ecs_desired_count` | 1 | 2+ for HA |
| `log_retention_days` | 1 | 30-90 |
| `rds_backup_retention_period` | 7 | 14-35 |
| `postgres_version` | 15 | Latest stable |
| Container Insights | disabled | enabled |
| `acm_certificate_arn` | empty (HTTP) | ACM cert (HTTPS) |
| `allowed_origins` | localhost | Production domain(s) only |
| `allowed_cidr_blocks` | `0.0.0.0/0` | Restrict to known IPs |
| `enable_alb` | true | true |
| Deletion protection | disabled | enabled (auto for prod) |

## Security Hardening Checklist

### Infrastructure

- [ ] **HTTPS** — Provide ACM certificate ARN to enable HTTPS with automatic HTTP redirect
- [ ] **Restrict ALB access** — Set `allowed_cidr_blocks` to known IP ranges instead of `0.0.0.0/0`
- [ ] **Enable Container Insights** — Set `containerInsights = "enabled"` in `ecs.tf` for production monitoring
- [ ] **Increase log retention** — Set `log_retention_days` to 30-90 for compliance
- [ ] **Multi-AZ NAT** — Consider NAT Gateway per AZ for high availability (increases cost)
- [ ] **VPC Flow Logs** — Enable for network monitoring and security analysis
- [ ] **Secrets Manager** — Database password is stored in Secrets Manager (auto-configured)

### Application

- [ ] **JWT authentication** — Set `AUTH_ENABLED=true` and configure JWKS URL
- [ ] **JWT secret key** — Use a strong, unique secret (or use JWKS with RS256)
- [ ] **CORS origins** — Remove localhost, add only production domain(s)
- [ ] **Rate limiting** — Verify limits are appropriate for production traffic

### Database

- [ ] **Instance sizing** — Right-size for production workload
- [ ] **Encryption at rest** — Enabled by default (`storage_encrypted = true`)
- [ ] **Automated backups** — Set retention period to 14-35 days for production
- [ ] **Password rotation** — Rotate credentials periodically via Secrets Manager

### Monitoring

- [ ] **CloudWatch alarms** — Set up alerts for ECS task failures, high CPU/memory, API errors, SQS queue depth
- [ ] **Health checks** — ALB health check is auto-configured at `/health`

## Azure Deployment Guidance

The application is cloud-agnostic. AWS-to-Azure service mapping:

| AWS Service | Azure Equivalent | Notes |
|-------------|------------------|-------|
| ECS Fargate | Azure Container Apps / AKS | Container Apps for simpler setup |
| RDS PostgreSQL | Azure Database for PostgreSQL | Flexible Server recommended |
| S3 | Azure Blob Storage | Use `CLOUD_PROVIDER=azure` |
| SQS | Azure Queue Storage | Use `CLOUD_PROVIDER=azure` |
| ALB | Azure Application Gateway | Or Azure Front Door |
| Secrets Manager | Azure Key Vault | For database password |
| ECR | Azure Container Registry | For Docker images |
| IAM OIDC | Azure AD Workload Identity | For GitHub Actions CI/CD |
| CloudWatch | Azure Monitor | Logs and metrics |

Key environment variables for Azure:
```bash
CLOUD_PROVIDER=azure
CLOUD_STORAGE_BUCKET=<container-name>
AZURE_STORAGE_ACCOUNT_NAME=<account-name>
```

## GCP Deployment Guidance

AWS-to-GCP service mapping:

| AWS Service | GCP Equivalent | Notes |
|-------------|----------------|-------|
| ECS Fargate | Cloud Run / GKE Autopilot | Cloud Run for simpler setup |
| RDS PostgreSQL | Cloud SQL for PostgreSQL | |
| S3 | Cloud Storage | Use `CLOUD_PROVIDER=gcp` |
| SQS | Cloud Pub/Sub | Use `CLOUD_PROVIDER=gcp` |
| ALB | Cloud Load Balancing | External HTTP(S) LB |
| Secrets Manager | Secret Manager | For database password |
| ECR | Artifact Registry | For Docker images |
| IAM OIDC | Workload Identity Federation | For GitHub Actions CI/CD |
| CloudWatch | Cloud Logging / Monitoring | |

Key environment variables for GCP:
```bash
CLOUD_PROVIDER=gcp
CLOUD_STORAGE_BUCKET=<bucket-name>
```

## Troubleshooting

### GitHub Actions Fails with "Access Denied"
1. Verify `AWS_ROLE_ARN` secret is correct
2. Check GitHub OIDC provider exists: `aws iam list-open-id-connect-providers`
3. Verify `github_repository` in `terraform.tfvars` matches your repo

### ECS Tasks Not Starting
1. Check CloudWatch Logs for errors
2. Verify container image exists in ECR
3. Check task definition image URI is correct
4. Verify security group allows outbound traffic

### Application Can't Access S3/SQS
1. Verify ECS task role has correct policies (check `iam_app.tf`)
2. Check resource ARNs in IAM policies match actual resources

### Database Connection Failed
1. Verify security group allows ECS tasks to access RDS (port 5432)
2. Check database endpoint and password are correct
3. Verify RDS is in the same VPC as ECS
