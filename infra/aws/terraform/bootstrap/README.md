# Terraform Backend Bootstrap

This directory contains the bootstrap Terraform configuration that creates the S3 bucket and DynamoDB table used for Terraform remote state.

## Why Bootstrap?

The main Terraform project uses remote state (S3 + DynamoDB), but those resources need to exist before we can use them. This creates a chicken-and-egg problem. The solution is to:

1. Create backend resources using **local state** (this bootstrap)
2. Then use **remote state** for the main project

## Usage

### One-Time Setup

```bash
cd infra/aws/terraform/bootstrap

# Initialize with local state
terraform init

# Set variables (or use terraform.tfvars)
export TF_VAR_environment=dev
export TF_VAR_project_name=import-export-orchestrator
export TF_VAR_aws_region=us-east-1

# Plan
terraform plan

# Apply (creates S3 bucket and DynamoDB table)
terraform apply
```

### After Bootstrap

Once the backend resources exist, the main Terraform project can use remote state. The bootstrap resources are managed separately and should rarely (if ever) need changes.

## Important Notes

- **Do NOT** add these resources to the main Terraform project
- **Do NOT** delete these resources (they hold your Terraform state!)
- Keep the bootstrap state file (`bootstrap.tfstate`) safe
- Consider backing up the bootstrap state file

## Resources Created

- S3 bucket: `{project_name}-terraform-state-{environment}-{account_id}`
- DynamoDB table: `{project_name}-terraform-state-lock-{environment}`

