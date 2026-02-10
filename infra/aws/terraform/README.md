# AWS Infrastructure

Terraform configuration for deploying Import/Export Orchestrator to AWS ECS/Fargate.

## Architecture

This application uses **shared infrastructure** (VPC, ECS Cluster, RDS) deployed separately. See `shared-infrastructure` project for the base layer.

```
Shared Infrastructure          Application Infrastructure
├── VPC + Subnets              ├── ALB + Target Group
├── ECS Cluster (Fargate)      ├── ECS Service + Task Definition
├── RDS PostgreSQL             ├── ECR Repository
└── NAT Gateway                ├── SQS Queue + DLQ
                               ├── S3 Bucket (exports)
                               ├── Security Groups
                               ├── IAM Roles
                               └── Secrets Manager
```

## Prerequisites

- Terraform >= 1.0
- AWS CLI configured
- **Shared infrastructure deployed** (VPC, ECS Cluster, RDS)
- **Database initialized by DBA** (see Step 2 below)

## Deployment Steps

### Step 1: Bootstrap State Backend (One-time)

```bash
cd bootstrap
terraform init
terraform apply
cd ..
```

### Step 2: Initialize Database (DBA Task)

Before deploying, a DBA must create the database on the shared RDS:

```bash
# Get RDS master password
aws secretsmanager get-secret-value \
  --secret-id "saasdog-shared-rds-master-password-dev" \
  --query 'SecretString' --output text

# Run init script (requires VPC access - use bastion/VPN)
psql -h <rds-endpoint> -U postgres -f ../../../scripts/init-database.sql
```

See `scripts/init-database.sql` for the initialization script.

### Step 3: Configure Variables

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit with shared infrastructure values from: terraform output (in shared-infrastructure)
```

Required values from shared-infrastructure:
- `shared_vpc_id`
- `shared_public_subnet_ids`
- `shared_private_subnet_ids`
- `shared_ecs_cluster_arn`
- `shared_ecs_cluster_name`
- `shared_rds_endpoint`
- `shared_rds_address`
- `shared_rds_security_group_id`
- `shared_rds_master_password_secret_arn`

### Step 4: Deploy Infrastructure

```bash
terraform init \
  -backend-config="bucket=saasdog-import-export-tfstate-dev" \
  -backend-config="key=terraform.tfstate" \
  -backend-config="region=us-east-1" \
  -backend-config="dynamodb_table=saasdog-import-export-tflock-dev"

terraform apply
```

### Step 5: Build and Push Docker Image

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $(terraform output -raw ecr_repository_url)

# Build for linux/amd64 (required for Fargate)
docker build --platform linux/amd64 -t $(terraform output -raw ecr_repository_url):latest .
docker push $(terraform output -raw ecr_repository_url):latest

# Force ECS deployment
aws ecs update-service \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --service $(terraform output -raw ecs_service_name) \
  --force-new-deployment
```

### Step 6: Verify Deployment

```bash
curl http://$(terraform output -raw alb_dns_name)/health
```

## Outputs

| Output | Description |
|--------|-------------|
| `alb_dns_name` | Application Load Balancer DNS |
| `alb_url` | Full HTTP URL |
| `ecr_repository_url` | ECR repository for Docker images |
| `ecs_cluster_name` | Shared ECS cluster name |
| `ecs_service_name` | ECS service name |
| `s3_bucket_name` | S3 bucket for exports |
| `sqs_queue_url` | SQS queue URL |
| `database_url_secret_arn` | Secrets Manager ARN for DATABASE_URL |
| `cicd_role_arn` | IAM role for GitHub Actions |

## CI/CD

After initial deployment, use GitHub Actions for deployments. Required secrets:

| Secret | Description |
|--------|-------------|
| `AWS_ROLE_ARN` | Output from `terraform output cicd_role_arn` |
| `TERRAFORM_TFVARS` | Contents of terraform.tfvars |

## Troubleshooting

### ECS Task Fails to Start

```bash
# Check recent events
aws ecs describe-services --cluster <cluster> --services <service> \
  --query 'services[0].events[:5]'

# Check task logs
aws logs tail /ecs/saasdog-import-export-dev --follow
```

### Database Connection Failed

1. Verify database was initialized: `psql -h <rds> -U job_runner -d job_runner -c "SELECT 1"`
2. Check DATABASE_URL secret: `aws secretsmanager get-secret-value --secret-id <secret-arn>`
3. Verify security group allows ECS → RDS on port 5432

### SQS Access Denied

Verify ECS task role has `sqs:GetQueueUrl` permission (check `ecs.tf`).
