# Terraform Import Guide

This guide explains how to import existing AWS resources into Terraform state, which is necessary when resources were created outside of Terraform or when fixing state management issues.

## Prerequisites

1. **Bootstrap resources created**: The S3 bucket and DynamoDB table for Terraform state must exist (see `infra/aws/terraform/bootstrap/`)
2. **AWS CLI configured**: You must have AWS credentials configured
3. **Terraform initialized**: Run `terraform init` in `infra/aws/terraform/`

## Quick Start

```bash
cd infra/aws/terraform

# Set environment variables (optional, defaults shown)
export ENVIRONMENT=dev
export PROJECT_NAME=import-export-orchestrator

# Run the import script
../../scripts/import-existing-resources.sh
```

## Manual Import Process

If you prefer to import resources manually, here are the commands:

```bash
cd infra/aws/terraform

# Initialize Terraform (if not done)
terraform init

# Import ECR repository
terraform import aws_ecr_repository.app import-export-orchestrator

# Import CloudWatch log group
terraform import aws_cloudwatch_log_group.ecs /ecs/import-export-orchestrator-dev

# Import IAM roles
terraform import aws_iam_role.ecs_task_execution import-export-orchestrator-ecs-task-execution-dev
terraform import aws_iam_role.ecs_task import-export-orchestrator-ecs-task-dev
terraform import aws_iam_role.cicd import-export-orchestrator-cicd-role-dev

# Import S3 bucket (replace ACCOUNT_ID with your AWS account ID)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
terraform import aws_s3_bucket.exports import-export-orchestrator-exports-dev-${ACCOUNT_ID}

# Import RDS parameter group
terraform import aws_db_parameter_group.main import-export-orchestrator-postgres-dev
```

## Verifying Imports

After importing, verify everything is correct:

```bash
# Check what's in state
terraform state list

# Run plan to see if there are any differences
terraform plan
```

The plan should show minimal or no changes for imported resources. If you see unexpected changes, you may need to adjust the Terraform configuration to match the actual AWS resources.

## Common Issues

### VPC Limit Exceeded

If you hit the VPC limit error (`VpcLimitExceeded`), you have two options:

#### Option 1: Delete Unused VPCs

```bash
# List all VPCs in us-east-1
aws ec2 describe-vpcs --region us-east-1 --query 'Vpcs[*].[VpcId,Tags[?Key==`Name`].Value|[0]]' --output table

# Delete unused VPCs (be careful!)
aws ec2 delete-vpc --vpc-id vpc-xxxxx
```

#### Option 2: Use Existing VPC

Modify `vpc.tf` to use an existing VPC via data source:

```hcl
# Instead of creating a new VPC, use an existing one
data "aws_vpc" "existing" {
  filter {
    name   = "tag:Name"
    values = ["your-existing-vpc-name"]
  }
}

# Then reference data.aws_vpc.existing.id instead of aws_vpc.main.id
```

### Resource Already Exists in State

If a resource is already in state, Terraform will skip the import. This is normal and expected.

### Resource Not Found

If a resource doesn't exist in AWS, you'll get an error. Either:
- Create the resource first, or
- Remove it from Terraform configuration if it's not needed

## Resources That Should NOT Be Imported

- **Backend resources** (S3 bucket, DynamoDB table): These are managed separately in `bootstrap/`
- **Resources that don't exist yet**: Create them with Terraform instead

## After Import

Once all imports are complete and `terraform plan` shows no unexpected changes:

1. Commit the updated state to version control (if using local state) OR
2. The state will be in the remote backend (S3) and ready for CI/CD
3. Push changes to GitHub - the `deploy.yml` workflow should now work correctly

## Troubleshooting

### State Lock Issues

If you get a state lock error:

```bash
# Check who has the lock
terraform force-unlock <LOCK_ID>
```

### Import Fails with "Resource not found"

1. Verify the resource exists in AWS:
   ```bash
   aws ec2 describe-vpcs --filters "Name=tag:Name,Values=import-export-orchestrator-vpc-dev"
   ```

2. Check the exact resource name/ID in AWS Console

3. Use the correct identifier format for the resource type

### Plan Shows Unexpected Changes After Import

This usually means the Terraform configuration doesn't match the actual AWS resource. Common causes:

- Tags are different
- Default values in AWS differ from Terraform defaults
- Resource was modified outside Terraform

Fix by either:
- Updating Terraform configuration to match AWS
- Running `terraform apply` to sync AWS to Terraform (if safe)

