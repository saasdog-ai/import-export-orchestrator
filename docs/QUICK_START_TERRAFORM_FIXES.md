# Quick Start: Terraform Deployment Fixes

This is a quick reference for fixing the GitHub Actions deployment issues.

## What Was Fixed

1. ✅ Backend resources separated into bootstrap configuration
2. ✅ Import script created for existing resources
3. ✅ VPC limit checker created
4. ✅ Documentation created

## What You Need to Do

### Step 1: Create Bootstrap Resources (One-Time)

```bash
cd infra/aws/terraform/bootstrap

# Initialize with local state
terraform init

# Apply (creates S3 bucket and DynamoDB table for Terraform state)
terraform apply
```

**Expected Output**: Creates:
- S3 bucket: `import-export-orchestrator-terraform-state-dev-{ACCOUNT_ID}`
- DynamoDB table: `import-export-orchestrator-terraform-state-lock-dev`

### Step 2: Import Existing Resources (One-Time)

```bash
cd infra/aws/terraform

# Run the import script
../../scripts/import-existing-resources.sh
```

**Expected Output**: Imports existing resources into Terraform state.

### Step 3: Verify Imports

```bash
# Check what's in state
terraform state list

# Run plan to verify
terraform plan
```

**Expected**: Plan should show minimal or no changes for imported resources.

### Step 4: Check VPC Limits (If Needed)

```bash
# Check if you're at VPC limit
./scripts/check-vpc-limits.sh
```

**If at limit**: Either delete unused VPCs or modify `vpc.tf` to use an existing VPC.

### Step 5: Push to GitHub

```bash
git add .
git commit -m "Fix Terraform deployment: separate backend, import existing resources"
git push
```

**Expected**: GitHub Actions workflow should now succeed! 🎉

## Troubleshooting

### "Resource already exists" in GitHub Actions

- Make sure you completed Step 2 (import existing resources)
- Verify: `terraform state list` shows the resources

### VPC limit errors

- Run `./scripts/check-vpc-limits.sh`
- Delete unused VPCs or use existing VPC

### Bootstrap fails

- Check AWS credentials: `aws sts get-caller-identity`
- Verify you have permissions to create S3 buckets and DynamoDB tables

## Need More Details?

- **Full guide**: See `docs/TERRAFORM_FIXES_SUMMARY.md`
- **Import details**: See `docs/TERRAFORM_IMPORT_GUIDE.md`
- **Bootstrap details**: See `infra/aws/terraform/bootstrap/README.md`

