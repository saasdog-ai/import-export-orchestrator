# Terraform Deployment Fixes Summary

This document summarizes the fixes made to resolve GitHub Actions deployment issues.

## Problem

The `deploy.yml` workflow was failing with errors like:
- `RepositoryAlreadyExistsException`
- `ResourceAlreadyExistsException`
- `BucketAlreadyExists`
- `ResourceInUseException`
- `VpcLimitExceeded`

The root cause was that Terraform was trying to create resources that already existed in AWS, but weren't in Terraform state.

## Solution

Three key fixes were implemented:

### 1. Separate Backend Resources (Bootstrap)

**Problem**: Terraform was trying to manage the S3 bucket and DynamoDB table used for remote state in the same state file, creating a chicken-and-egg problem.

**Solution**: Created a separate bootstrap Terraform configuration that manages backend resources with local state.

**Location**: `infra/aws/terraform/bootstrap/`

**Action Required**: Run bootstrap once manually:
```bash
cd infra/aws/terraform/bootstrap
terraform init
terraform apply
```

**Files Changed**:
- Created `infra/aws/terraform/bootstrap/main.tf` - Bootstrap configuration
- Created `infra/aws/terraform/bootstrap/README.md` - Bootstrap instructions
- Removed backend resources from `infra/aws/terraform/iam_cicd.tf`
- Updated IAM policy in `iam_cicd.tf` to use ARN patterns instead of resource references

### 2. Import Existing Resources

**Problem**: Resources created outside Terraform (or in previous failed runs) weren't in Terraform state.

**Solution**: Created an import script to bring existing resources into Terraform state.

**Location**: `scripts/import-existing-resources.sh`

**Action Required**: Run import script once locally:
```bash
cd infra/aws/terraform
../../scripts/import-existing-resources.sh
```

**Resources to Import**:
- ECR repository: `import-export-orchestrator`
- CloudWatch log group: `/ecs/import-export-orchestrator-dev`
- IAM roles:
  - `import-export-orchestrator-ecs-task-execution-dev`
  - `import-export-orchestrator-ecs-task-dev`
  - `import-export-orchestrator-cicd-role-dev`
- S3 bucket: `import-export-orchestrator-exports-dev-{ACCOUNT_ID}`
- RDS parameter group: `import-export-orchestrator-postgres-dev`

**Documentation**: See `docs/TERRAFORM_IMPORT_GUIDE.md` for detailed instructions.

### 3. VPC Limit Handling

**Problem**: AWS accounts have a default limit of 5 VPCs per region. If you've hit this limit, Terraform can't create a new VPC.

**Solution**: Created a script to check VPC limits and list existing VPCs.

**Location**: `scripts/check-vpc-limits.sh`

**Action Required**: 
1. Check your VPC count:
   ```bash
   ./scripts/check-vpc-limits.sh
   ```

2. If at limit, either:
   - **Option A**: Delete unused VPCs
   - **Option B**: Modify `vpc.tf` to use an existing VPC via data source

## Workflow Changes

The `deploy.yml` workflow was simplified to remove automatic import logic. It now:
1. Initializes Terraform with remote backend
2. Validates and formats code
3. Runs `terraform plan`
4. Runs `terraform apply` (on main branch)

No more complex state/import dance - just standard Terraform workflow.

## Step-by-Step Setup

### Prerequisites
1. AWS CLI configured
2. Terraform installed
3. Bootstrap resources created (see above)

### One-Time Setup

1. **Create bootstrap resources**:
   ```bash
   cd infra/aws/terraform/bootstrap
   terraform init
   terraform apply
   ```

2. **Import existing resources**:
   ```bash
   cd infra/aws/terraform
   ../../scripts/import-existing-resources.sh
   ```

3. **Verify imports**:
   ```bash
   terraform plan
   ```
   Should show minimal or no changes for imported resources.

4. **Check VPC limits** (if needed):
   ```bash
   ./scripts/check-vpc-limits.sh
   ```

5. **Commit and push**:
   ```bash
   git add .
   git commit -m "Fix Terraform deployment: separate backend, import existing resources"
   git push
   ```

### After Setup

The GitHub Actions workflow should now work correctly. It will:
- Use remote state (S3 + DynamoDB)
- Only create resources that don't exist
- Update resources that are already in state

## Files Created/Modified

### New Files
- `infra/aws/terraform/bootstrap/main.tf` - Bootstrap Terraform config
- `infra/aws/terraform/bootstrap/README.md` - Bootstrap documentation
- `scripts/import-existing-resources.sh` - Import script
- `scripts/check-vpc-limits.sh` - VPC limit checker
- `docs/TERRAFORM_IMPORT_GUIDE.md` - Detailed import guide
- `docs/TERRAFORM_FIXES_SUMMARY.md` - This file

### Modified Files
- `infra/aws/terraform/iam_cicd.tf` - Removed backend resources, updated IAM policy

## Verification

After completing the setup:

1. **Local verification**:
   ```bash
   cd infra/aws/terraform
   terraform plan
   ```
   Should show no unexpected changes.

2. **GitHub Actions**: Push to main branch and verify the workflow succeeds.

## Troubleshooting

### "Resource already exists" errors persist

- Make sure you ran the import script
- Verify resources are in state: `terraform state list`
- Check that backend is correctly configured in GitHub Actions

### VPC limit errors

- Run `./scripts/check-vpc-limits.sh` to see current VPCs
- Delete unused VPCs or use an existing VPC

### State lock errors

- Check if another Terraform run is in progress
- If stuck, use `terraform force-unlock <LOCK_ID>`

## Best Practices Going Forward

1. **Always use remote state** - Don't commit `.tfstate` files
2. **Import before creating** - If a resource exists, import it first
3. **Separate concerns** - Backend resources managed separately
4. **Test locally first** - Run `terraform plan` before pushing

