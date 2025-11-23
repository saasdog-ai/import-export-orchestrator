# AWS Deployment Guide

This guide provides step-by-step instructions for deploying the Import/Export Orchestrator to AWS.

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI installed and configured (`aws configure`)
- Terraform >= 1.0 installed
- GitHub repository with Actions enabled
- Docker installed (for building container images)

## Architecture

The application is deployed on AWS using:
- **ECS Fargate**: Container orchestration
- **RDS PostgreSQL**: Managed database
- **S3**: Export file storage
- **SQS**: Message queue for job processing
- **ALB**: Application Load Balancer (optional)

## Deployment Steps

### Step 1: Configure AWS CLI

```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Enter default region (e.g., us-east-1)
# Enter default output format (json)
```

### Step 2: Configure Terraform Variables

```bash
cd infra/aws/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

```hcl
aws_region              = "us-east-1"
environment             = "dev"
project_name            = "import-export-orchestrator"
github_repository       = "your-username/import-export-orchestrator"

# Database configuration
database_instance_class = "db.t3.micro"
database_allocated_storage = 20
database_name           = "job_runner"
database_username       = "postgres"

# ECS configuration
ecs_task_cpu            = 512
ecs_task_memory         = 1024
ecs_desired_count       = 1
enable_alb              = false  # Set to true if you need a load balancer

# SQS configuration
sqs_visibility_timeout  = 300
sqs_receive_wait_time   = 20
sqs_max_receive_count   = 3
```

**Important**: Never commit `terraform.tfvars` to version control!

### Step 3: Set Database Password

```bash
export TF_VAR_database_password="your-secure-password-here"
```

### Step 4: Initial Deployment (Bootstrap - One Time Only)

This initial deployment creates all infrastructure including the CI/CD role that GitHub Actions will use.

```bash
cd infra/aws/terraform
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

This creates:
- VPC and networking
- RDS PostgreSQL database
- ECS cluster and service
- S3 bucket for exports
- SQS queue for job processing
- IAM roles and policies
- Terraform state bucket and DynamoDB table
- GitHub OIDC provider

**⚠️ Important**: This is the **only time** you should run `terraform apply` locally. After this, all deployments go through GitHub Actions.

### Step 5: Get CI/CD Role ARN

```bash
terraform output cicd_role_arn
```

Copy the ARN (e.g., `arn:aws:iam::123456789012:role/import-export-orchestrator-cicd-role-dev`)

### Step 6: Configure GitHub Secrets

Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions**

Add the following secrets:

1. **`AWS_ROLE_ARN`**: The CI/CD role ARN from Step 5
2. **`DATABASE_PASSWORD`**: Your database password
3. **`AWS_REGION`**: AWS region (e.g., `us-east-1`)

### Step 7: Build and Push Docker Image

The GitHub Actions workflow (`.github/workflows/build-and-push-image.yml`) will automatically build and push the Docker image to ECR when you push to the repository.

Alternatively, build and push manually:

```bash
# Get ECR repository URL
cd infra/aws/terraform
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

### Step 8: Update Terraform with Image URI

Update `terraform.tfvars`:

```hcl
container_image = "{account-id}.dkr.ecr.us-east-1.amazonaws.com/import-export-orchestrator:latest"
```

Replace `{account-id}` with your AWS account ID (from `terraform output`).

Then apply:

```bash
terraform apply -var-file="terraform.tfvars"
```

### Step 9: Ongoing Deployments via CI/CD

After the initial bootstrap, **all deployments should go through GitHub Actions**:

1. Push code to `main` branch → Automatically deploys
2. Or manually trigger: **Actions** → **Deploy to AWS** → **Run workflow**

The GitHub Actions workflow (`.github/workflows/deploy.yml`) will:
- Build and push Docker image to ECR
- Run Terraform plan/apply
- Deploy infrastructure changes

## Verify Deployment

### Check ECS Service

```bash
aws ecs describe-services \
  --cluster import-export-orchestrator-cluster-dev \
  --services import-export-orchestrator-service-dev
```

### Check Application Health

If ALB is enabled:

```bash
terraform output alb_dns_name
curl https://{alb-dns-name}/health
```

### Check CloudWatch Logs

```bash
aws logs tail /ecs/import-export-orchestrator-dev --follow
```

## Troubleshooting

### GitHub Actions Fails with "Access Denied"

1. Verify `AWS_ROLE_ARN` secret is correct
2. Check that GitHub OIDC provider exists: `aws iam list-open-id-connect-providers`
3. Verify repository name matches `github_repository` in `terraform.tfvars`

### ECS Tasks Not Starting

1. Check CloudWatch Logs for errors
2. Verify container image exists in ECR
3. Check task definition for correct image URI
4. Verify security group allows outbound traffic

### Application Can't Access S3/SQS

1. Verify ECS task role has correct policies
2. Check resource ARNs in IAM policies match actual resources

### Database Connection Failed

1. Verify security group allows ECS tasks to access RDS
2. Check database endpoint is correct
3. Verify database password is correct

## Security Best Practices

1. **Never commit secrets**: Use environment variables or AWS Secrets Manager
2. **Use least privilege**: IAM roles have minimum required permissions
3. **Enable encryption**: S3 buckets, RDS, and EBS volumes are encrypted
4. **Network isolation**: ECS tasks run in private subnets
5. **Regular updates**: Keep container images and dependencies updated

