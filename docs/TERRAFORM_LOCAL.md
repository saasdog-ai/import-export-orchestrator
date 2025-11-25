# Running Terraform Locally

This guide explains how to run Terraform from your local machine to manage AWS infrastructure.

## Prerequisites

1. **AWS CLI configured**: `aws configure` or `aws sso login`
2. **Terraform installed**: `brew install terraform` (or download from terraform.io)
3. **Database password**: Set `TF_VAR_database_password` environment variable

## Quick Start

### 1. Set up environment variables

```bash
export TF_VAR_database_password="your-database-password"
```

### 2. Navigate to Terraform directory

```bash
cd infra/aws/terraform
```

### 3. Initialize Terraform

```bash
terraform init
```

### 4. Use the helper script

```bash
# From project root
./scripts/terraform-local.sh help
```

## Common Tasks

### Recreate ECS Tasks

If you need to recreate ECS tasks (e.g., after updating the Docker image):

```bash
./scripts/terraform-local.sh recreate-ecs
```

This will:
1. Taint the ECS task definition (forces recreation)
2. Taint the ECS service (forces recreation)
3. Apply changes to recreate everything

### Plan Changes

See what Terraform will do before applying:

```bash
./scripts/terraform-local.sh plan
```

### Apply Changes

Apply all Terraform changes:

```bash
./scripts/terraform-local.sh apply
```

### Check Current State

List all resources in state:

```bash
./scripts/terraform-local.sh state-list
```

Show details of a specific resource:

```bash
./scripts/terraform-local.sh state-show aws_ecs_service.main
```

### View Outputs

See Terraform outputs (endpoints, ARNs, etc.):

```bash
./scripts/terraform-local.sh output
```

## Manual Terraform Commands

If you prefer to run Terraform commands directly:

```bash
cd infra/aws/terraform

# Initialize
terraform init

# Plan
terraform plan -var-file="terraform.tfvars"

# Apply
terraform apply -var-file="terraform.tfvars"

# Destroy (be careful!)
terraform destroy -var-file="terraform.tfvars"
```

## State Management

### Using Remote State (S3 Backend)

If you want to use remote state (recommended for team collaboration):

1. Uncomment the backend configuration in `main.tf`:

```hcl
backend "s3" {
  bucket         = "import-export-orchestrator-terraform-state-dev-{account-id}"
  key            = "terraform.tfstate"
  region         = "us-east-1"
  encrypt        = true
  dynamodb_table = "import-export-orchestrator-terraform-state-lock-dev"
}
```

2. Replace `{account-id}` with your AWS account ID
3. Run `terraform init` to migrate state

### Using Local State

By default, Terraform uses local state (stored in `terraform.tfstate`). This is fine for:
- Personal development
- Testing
- One-person projects

**Note**: Never commit `terraform.tfstate` to version control!

## Troubleshooting

### "Error: No valid credential sources found"

Make sure AWS credentials are configured:

```bash
aws sts get-caller-identity
```

If this fails, run:
```bash
aws configure
# or
aws sso login
```

### "Error: database_password is required"

Set the environment variable:

```bash
export TF_VAR_database_password="your-password"
```

Or edit `terraform.tfvars` and set `database_password` directly (not recommended for production).

### "Error: Backend configuration changed"

If you switch between local and remote state, you need to reinitialize:

```bash
terraform init -migrate-state
```

### ECS Tasks Not Updating

If ECS tasks aren't updating after applying changes:

1. Check if the task definition changed:
   ```bash
   terraform plan -var-file="terraform.tfvars" | grep aws_ecs_task_definition
   ```

2. Force recreation:
   ```bash
   ./scripts/terraform-local.sh recreate-ecs
   ```

3. Or manually taint and apply:
   ```bash
   terraform taint aws_ecs_task_definition.main
   terraform taint aws_ecs_service.main
   terraform apply -var-file="terraform.tfvars"
   ```

## Best Practices

1. **Always run `terraform plan` before `terraform apply`**
2. **Use remote state for team collaboration**
3. **Never commit `terraform.tfstate` or `terraform.tfvars`**
4. **Use environment variables for sensitive values** (like database passwords)
5. **Review changes carefully before applying**
6. **Use `terraform fmt` to format your code**

## Resources

- [Terraform AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Terraform Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/index.html)

