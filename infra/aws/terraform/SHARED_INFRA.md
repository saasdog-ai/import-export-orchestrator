# Shared Infrastructure Mode

This Terraform configuration supports two deployment modes:

1. **Standalone Mode** (`use_shared_infra = false`): Creates all infrastructure (VPC, ECS cluster, RDS, etc.)
2. **Shared Mode** (`use_shared_infra = true`): Uses existing shared infrastructure

## Architecture Overview

When multiple SaasDog projects (import-export-orchestrator, integration-platform) are deployed together, they can share:

- VPC and subnets
- ECS cluster (different services/tasks in same cluster)
- RDS instance (different databases in same PostgreSQL instance)
- Security groups (ALB, ECS, RDS)

Each project always creates its own:
- ECR repository
- ECS task definition and service
- S3 bucket
- SQS queues
- CloudWatch log groups
- IAM roles and policies
- ALB (each project has its own load balancer)

## Naming Convention

Shared resources use the `shared_project_name` prefix (default: `saasdog-ai`):
- Cluster: `saasdog-ai-cluster-dev`
- VPC: `saasdog-ai-vpc-dev`
- RDS: `saasdog-ai-db-dev`

Project-specific resources use the `project_name`:
- Service: `import-export-orchestrator-service-dev`
- Task: `import-export-orchestrator-dev`

## Deployment Scenarios

### Scenario 1: Customer Buys Only import-export-orchestrator

Deploy with defaults:
```hcl
use_shared_infra = false  # Creates all infrastructure
shared_project_name = "saasdog-ai"  # Names shared resources generically
```

If they later add integration-platform, it can use shared mode.

### Scenario 2: Customer Buys Only integration-platform

Deploy with:
```hcl
use_shared_infra = false  # Creates all infrastructure
```

Uses its own naming (`integration-platform-*`).

### Scenario 3: Customer Buys Both Projects

**Option A: Deploy import-export-orchestrator first**
1. Deploy import-export-orchestrator with `use_shared_infra = false`
2. Run `terraform output shared_infra_tfvars` to get shared values
3. Deploy integration-platform with those shared values

**Option B: Deploy integration-platform first**
1. Deploy integration-platform with `use_shared_infra = false`
2. Deploy import-export-orchestrator with `use_shared_infra = true`

## Getting Shared Infrastructure Values

After deploying the first project, run:

```bash
terraform output -raw shared_infra_tfvars
```

This outputs a ready-to-copy tfvars snippet for the second project.

## Migration: Renaming Existing Cluster

If you have an existing cluster named `import-export-orchestrator-cluster-dev` and want to rename it to `saasdog-ai-cluster-dev`:

### Option 1: Create New, Migrate, Delete Old (Recommended)

1. Create new shared infrastructure with generic names
2. Update ECS services to use new cluster
3. Delete old cluster

### Option 2: Terraform State Move (Advanced)

```bash
# Rename in state only (resource stays the same in AWS)
terraform state mv \
  'aws_ecs_cluster.main' \
  'aws_ecs_cluster.main[0]'
```

Note: Actual AWS resource name change requires recreating the cluster.

## Variables Reference

| Variable | Type | Description |
|----------|------|-------------|
| `use_shared_infra` | bool | Enable shared infrastructure mode |
| `shared_project_name` | string | Prefix for shared resource names |
| `shared_vpc_id` | string | VPC ID to use in shared mode |
| `shared_public_subnet_ids` | list | Public subnet IDs |
| `shared_private_subnet_ids` | list | Private subnet IDs |
| `shared_alb_security_group_id` | string | ALB security group ID |
| `shared_ecs_security_group_id` | string | ECS tasks security group ID |
| `shared_rds_security_group_id` | string | RDS security group ID |
| `shared_ecs_cluster_arn` | string | ECS cluster ARN |
| `shared_rds_endpoint` | string | RDS endpoint (host:port) |
| `shared_db_credentials_secret_arn` | string | Secrets Manager ARN for DB credentials |

## Database Strategy

When sharing an RDS instance:

1. **Separate databases**: Each project uses a different database name in the same PostgreSQL instance
   - import-export-orchestrator: `job_runner`
   - integration-platform: `integration_platform`

2. **Separate credentials**: Each project can have its own Secrets Manager secret pointing to the shared RDS

3. **Independent migrations**: Each project manages its own schema with Alembic

## Cost Savings

Sharing infrastructure can significantly reduce AWS costs:

| Resource | Standalone (2 projects) | Shared |
|----------|-------------------------|--------|
| NAT Gateway | 2 × $32/month | 1 × $32/month |
| RDS (db.t3.micro) | 2 × $15/month | 1 × $15/month |
| ECS cluster | Free | Free |
| **Monthly savings** | - | ~$47/month |
