# Testing Resource Imports Locally

This guide helps you test the resource import functionality locally before running it in GitHub Actions.

## Prerequisites

1. **AWS CLI configured**:
   ```bash
   aws configure
   # Or use AWS_PROFILE
   export AWS_PROFILE=your-profile
   ```

2. **Terraform installed**:
   ```bash
   terraform version
   ```

3. **Set database password** (if not in terraform.tfvars):
   ```bash
   export TF_VAR_database_password="your-password"
   ```

## Running the Test

```bash
# Test with dev environment (default)
./scripts/test-import-resources.sh dev

# Or specify a different environment
./scripts/test-import-resources.sh staging
```

## What It Does

The script will:
1. Check AWS account ID
2. Initialize Terraform
3. Attempt to import existing resources:
   - ECR repository
   - IAM roles (ECS task execution, ECS task)
   - CloudWatch log group
   - S3 buckets (exports, terraform state)
   - DynamoDB table (terraform state lock)
   - RDS resources (subnet group, parameter group)
   - OIDC provider

## Expected Output

- ✅ Resources that exist and import successfully
- ⚠️ Resources that don't exist (this is OK - they'll be created)
- ⚠️ Resources that fail to import (check error messages)

## Verifying Imports

After running the script, verify what was imported:

```bash
cd infra/aws/terraform
terraform state list
```

## Troubleshooting

### Error: "Could not get AWS account ID"
- Make sure AWS CLI is configured: `aws configure`
- Or set `AWS_PROFILE` environment variable

### Error: "var.database_password"
- Set the environment variable: `export TF_VAR_database_password="your-password"`
- Or ensure it's in `terraform.tfvars`

### Import fails with "Invalid count argument"
- This is a validation error that doesn't prevent import
- The script should detect successful imports despite these errors

### Resource not found
- This is OK - the resource will be created by Terraform
- The import step is optional and only for existing resources
