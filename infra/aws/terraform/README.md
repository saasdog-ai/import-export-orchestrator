# AWS Infrastructure

This directory contains Terraform configuration for deploying the import-export-orchestrator to AWS ECS/Fargate.

## Prerequisites

- Terraform >= 1.0
- AWS CLI configured (or environment variables set)
- AWS account with appropriate permissions

## Authentication

**IMPORTANT:** Never store AWS credentials in Terraform files. Use one of these methods:

1. **AWS CLI Profile** (Recommended for local development):
   ```bash
   aws configure --profile your-profile
   export AWS_PROFILE=your-profile
   ```

2. **Environment Variables**:
   ```bash
   export AWS_ACCESS_KEY_ID=your-access-key
   export AWS_SECRET_ACCESS_KEY=your-secret-key
   export AWS_REGION=us-east-1
   ```

3. **IAM Instance Profile** (for EC2 instances running Terraform)

4. **GitHub Actions OIDC** (for CI/CD - see `.github/workflows/deploy.yml`)

## Usage

1. **Copy example variables file**:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. **Edit terraform.tfvars** with your values (DO NOT commit this file)

3. **Set database password via environment variable**:
   ```bash
   export TF_VAR_database_password="your-secure-password"
   ```
   Or use AWS Secrets Manager (recommended for production).

4. **Initialize Terraform**:
   ```bash
   terraform init
   ```

5. **Plan the deployment**:
   ```bash
   terraform plan -var-file="terraform.tfvars"
   ```

6. **Apply the configuration**:
   ```bash
   terraform apply -var-file="terraform.tfvars"
   ```

7. **Destroy resources** (when done):
   ```bash
   terraform destroy -var-file="terraform.tfvars"
   ```

## Infrastructure Components

- **VPC**: Custom VPC with public and private subnets
- **RDS**: PostgreSQL database instance
- **ECS Cluster**: Fargate cluster for running containers
- **ECS Service**: Service running the application
- **ALB**: Application Load Balancer (optional)
- **S3 Bucket**: For storing export files with versioning and lifecycle policies
- **SQS Queue**: For job processing with dead letter queue for failed messages
- **Security Groups**: Network access control
- **IAM Roles**: Task execution and task roles for ECS (with S3 and SQS permissions)

## Outputs

After applying, Terraform will output:
- VPC ID
- RDS endpoint
- ECS cluster name
- ALB DNS name (if enabled)
- S3 bucket name and ARN
- SQS queue URL, ARN, and name
- SQS dead letter queue URL

## Production Considerations

1. **Use AWS Secrets Manager** for database passwords
2. **Enable RDS backups** and configure retention
3. **Use multiple availability zones** for high availability
4. **Restrict ALB CIDR blocks** to known IPs
5. **Enable CloudWatch alarms** for monitoring
6. **Use Terraform remote state** (S3 + DynamoDB)
7. **Implement proper IAM policies** for least privilege

