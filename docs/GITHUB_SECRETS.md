# GitHub Secrets Configuration

This document lists all the secrets and environment variables required for GitHub Actions workflows.

## Required Secrets

You need to configure these secrets in GitHub for the workflows to function:

### 1. `AWS_ROLE_ARN` ✅ (Already Added)

**Purpose**: ARN of the CI/CD IAM role for OIDC authentication

**Where to get it**: After running the initial Terraform deployment:
```bash
cd infra/aws/terraform
terraform output cicd_role_arn
```

**Example value**:
```
arn:aws:iam::123456789012:role/import-export-orchestrator-cicd-role-dev
```

**Used by**:
- `build-and-push-image.yml` workflow
- `deploy.yml` workflow

---

### 2. `DATABASE_PASSWORD` ❌ (Required - Not Yet Added)

**Purpose**: Master password for the RDS PostgreSQL database

**Where to get it**: This is the password you set when running the initial Terraform deployment:
```bash
export TF_VAR_database_password="your-secure-password"
```

**Example value**:
```
MySecurePassword123!
```

**Used by**:
- `deploy.yml` workflow (for Terraform to create/update RDS)

**Security Note**: Use a strong password (at least 16 characters, mix of letters, numbers, and special characters)

---

## How to Add Secrets

### Option 1: Environment-Specific Secrets (Recommended)

1. Go to your GitHub repository → **Settings** → **Environments**
2. If the environment doesn't exist (e.g., `dev`), click **New environment** and create it
3. Click on the environment (e.g., `dev`)
4. Under **Secrets**, click **Add secret**
5. Add each secret:
   - Name: `AWS_ROLE_ARN`
   - Value: (paste the ARN from `terraform output cicd_role_arn`)
   - Name: `DATABASE_PASSWORD`
   - Value: (paste your database password)

### Option 2: Repository-Level Secrets (Fallback)

1. Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add each secret:
   - Name: `AWS_ROLE_ARN`
   - Value: (paste the ARN)
   - Name: `DATABASE_PASSWORD`
   - Value: (paste your database password)

**Note**: If you use environment-specific secrets, the workflow will use those. If not found, it will fall back to repository-level secrets.

---

## Automatically Set Variables (No Configuration Needed)

These are automatically set by GitHub Actions - you don't need to configure them:

- **`TF_VAR_github_repository`**: Automatically set to `${{ github.repository }}` (e.g., `rajivskumar/import-export-orchestrator`)
- **`TF_VAR_environment`**: Automatically set from workflow input (defaults to `dev`)
- **`AWS_REGION`**: Hardcoded to `us-east-1` in workflows

---

## Verification

After adding the secrets, you can verify they're configured:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. You should see both secrets listed (values are hidden for security)

Or check the environment:
1. Go to **Settings** → **Environments** → Select your environment (e.g., `dev`)
2. Under **Secrets**, you should see both secrets listed

---

## Troubleshooting

### Error: "Credentials could not be loaded"

**Cause**: `AWS_ROLE_ARN` secret is missing or empty

**Solution**: 
1. Verify the secret is set in the environment or repository
2. Check that the ARN is correct (should start with `arn:aws:iam::`)
3. Ensure the environment name matches (e.g., `dev`)

### Error: "No value for required variable 'database_password'"

**Cause**: `DATABASE_PASSWORD` secret is missing

**Solution**:
1. Add `DATABASE_PASSWORD` secret to the environment or repository
2. Use the same password you used during initial Terraform deployment

### Error: "Access Denied" when assuming role

**Cause**: The IAM role trust policy doesn't allow the GitHub repository

**Solution**:
1. Verify `github_repository` in `terraform.tfvars` matches your actual repository
2. Check the IAM role trust policy allows your GitHub repository
3. Ensure the GitHub OIDC provider exists in AWS

---

## Summary Checklist

- [x] `AWS_ROLE_ARN` - Added
- [ ] `DATABASE_PASSWORD` - **Need to add this**

Once both secrets are configured, your workflows should be able to:
- ✅ Build and push Docker images to ECR
- ✅ Deploy infrastructure to AWS using Terraform

