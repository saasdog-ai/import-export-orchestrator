# AWS Authentication via GitHub OIDC

This document explains how GitHub Actions authenticates to AWS **without storing access keys or secrets**.

## How It Works

GitHub Actions uses **OIDC (OpenID Connect)** to authenticate to AWS. This is more secure than using long-lived access keys because:

1. ✅ **No access keys stored** - No AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY needed
2. ✅ **Short-lived tokens** - Each workflow run gets a temporary token
3. ✅ **Repository-scoped** - Only your specific repository can assume the role
4. ✅ **Audit trail** - All authentication is logged in CloudTrail

## Authentication Flow

```
┌─────────────────┐
│  GitHub Actions │
│   (Workflow)    │
└────────┬────────┘
         │
         │ 1. Request OIDC token from GitHub
         ▼
┌─────────────────┐
│  GitHub OIDC    │
│  Provider       │
└────────┬────────┘
         │
         │ 2. Issue OIDC token (JWT)
         ▼
┌─────────────────┐
│  AWS Actions    │
│  configure-aws  │
│  -credentials   │
└────────┬────────┘
         │
         │ 3. Exchange OIDC token for AWS credentials
         ▼
┌─────────────────┐
│  AWS STS        │
│  (Security      │
│   Token Service)│
└────────┬────────┘
         │
         │ 4. Validate token & check IAM role trust policy
         ▼
┌─────────────────┐
│  IAM Role       │
│  (CI/CD Role)   │
└────────┬────────┘
         │
         │ 5. Return temporary AWS credentials
         ▼
┌─────────────────┐
│  GitHub Actions │
│  (Can now use   │
│   AWS services) │
└─────────────────┘
```

## Components

### 1. GitHub Workflow Configuration

The workflow needs two things:

```yaml
permissions:
  id-token: write  # Required for OIDC - allows workflow to request OIDC token
  contents: read

steps:
  - name: Configure AWS credentials using OIDC
    uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: ${{ secrets.AWS_ROLE_ARN }}  # The IAM role ARN
      aws-region: us-east-1
```

### 2. AWS IAM OIDC Provider

Created by Terraform in `infra/aws/terraform/iam_cicd.tf`:

```hcl
resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
  
  client_id_list = ["sts.amazonaws.com"]
  
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1"  # GitHub's OIDC thumbprint
  ]
}
```

This tells AWS: "Trust tokens issued by GitHub Actions"

### 3. IAM Role with Trust Policy

The CI/CD IAM role allows GitHub to assume it:

```hcl
resource "aws_iam_role" "cicd" {
  assume_role_policy = jsonencode({
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.github.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          # Only allow YOUR repository
          "token.actions.githubusercontent.com:sub" = "repo:rajivskumar/import-export-orchestrator:*"
        }
      }
    }]
  })
}
```

**Key Security Points:**
- `Principal: Federated` - Only the GitHub OIDC provider can assume this role
- `Condition: StringLike` - Only your specific repository can use this role
- `Action: sts:AssumeRoleWithWebIdentity` - Uses OIDC, not access keys

## What You Need to Configure

### In GitHub (One-Time Setup)

1. **Add `AWS_ROLE_ARN` secret**:
   - Go to Settings → Secrets and variables → Actions
   - Or Settings → Environments → `dev` → Secrets
   - Add secret: `AWS_ROLE_ARN` = `arn:aws:iam::123456789012:role/import-export-orchestrator-cicd-role-dev`
   - Get the ARN from: `terraform output cicd_role_arn`

### In AWS (Created by Terraform)

1. **OIDC Provider** - Created automatically by Terraform
2. **IAM Role** - Created automatically by Terraform with proper trust policy
3. **IAM Policies** - Attached to the role for required permissions

## Verification

### Check OIDC Provider Exists

```bash
aws iam list-open-id-connect-providers
```

Should show:
```
https://token.actions.githubusercontent.com
```

### Check IAM Role Trust Policy

```bash
aws iam get-role --role-name import-export-orchestrator-cicd-role-dev
```

Look for `AssumeRolePolicyDocument` - it should have:
- `Principal.Federated` pointing to the OIDC provider
- `Condition.StringLike` restricting to your repository

### Test in GitHub Actions

When the workflow runs, check the logs for:
```
✅ AWS_ROLE_ARN secret is configured
Configure AWS credentials using OIDC
```

If authentication fails, you'll see:
```
Error: Credentials could not be loaded
```

## Troubleshooting

### Error: "Credentials could not be loaded"

**Possible causes:**
1. `AWS_ROLE_ARN` secret not set in GitHub
2. IAM role doesn't exist in AWS
3. OIDC provider not created
4. Repository name mismatch in trust policy

**Solution:**
1. Verify secret is set: GitHub → Settings → Secrets
2. Check role exists: `aws iam get-role --role-name import-export-orchestrator-cicd-role-dev`
3. Check OIDC provider: `aws iam list-open-id-connect-providers`
4. Verify `github_repository` in `terraform.tfvars` matches your actual repo

### Error: "Access Denied" when assuming role

**Possible causes:**
1. Trust policy doesn't allow your repository
2. OIDC provider thumbprint is incorrect
3. Repository name in trust policy doesn't match

**Solution:**
1. Check trust policy: `aws iam get-role --role-name import-export-orchestrator-cicd-role-dev`
2. Verify repository name in trust policy matches: `repo:your-username/your-repo:*`
3. Re-run Terraform to update trust policy if needed

### Error: "OIDC provider already exists"

**Cause:** OIDC provider is account-wide (one per account), not per-resource

**Solution:** This is fine! Terraform will use the existing provider. The error is harmless.

## Security Best Practices

1. ✅ **Use OIDC** - Never use access keys in GitHub Actions
2. ✅ **Repository-scoped** - Trust policy restricts to your specific repository
3. ✅ **Least privilege** - IAM role only has permissions needed for deployment
4. ✅ **Short-lived tokens** - Each workflow run gets a new temporary token
5. ✅ **Audit trail** - All role assumptions are logged in CloudTrail

## Comparison: OIDC vs Access Keys

| Feature | OIDC (Current) | Access Keys (Not Recommended) |
|---------|----------------|-------------------------------|
| Storage | No secrets needed | Store AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY |
| Rotation | Automatic | Manual rotation required |
| Scope | Repository-specific | Account-wide |
| Audit | CloudTrail logs | CloudTrail logs |
| Security | ✅ More secure | ⚠️ Less secure |
| Setup | One-time (Terraform) | Manual key creation |

## Summary

**You don't need to provide access keys!** The authentication works like this:

1. GitHub Actions requests an OIDC token from GitHub
2. The `aws-actions/configure-aws-credentials` action exchanges this token for AWS credentials
3. AWS validates the token against the OIDC provider and IAM role trust policy
4. If valid, AWS returns temporary credentials (valid for 1 hour)
5. GitHub Actions uses these credentials to access AWS services

All you need is the `AWS_ROLE_ARN` secret pointing to the IAM role that Terraform created.

