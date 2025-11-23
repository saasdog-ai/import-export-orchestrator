# AWS Resource Naming Best Practices

## Overview

AWS resource naming conventions vary by service. Some resources must be globally unique, while others only need to be unique within an account.

## Resources That MUST Include Account ID

### 1. S3 Buckets
**Why**: S3 bucket names are **globally unique** across all AWS accounts worldwide.

**Current Implementation**:
```hcl
bucket = "${var.project_name}-exports-${var.environment}-${data.aws_caller_identity.current.account_id}"
```

**Best Practice**: ✅ Always include account ID (or another globally unique identifier)

**Example**:
- ✅ `import-export-orchestrator-exports-dev-123456789012`
- ❌ `import-export-orchestrator-exports-dev` (might conflict with another account)

### 2. IAM Role Names (Optional but Recommended)
**Why**: While not required, including account ID helps with:
- Cross-account resource identification
- Multi-account strategies
- Avoiding naming conflicts

**Current Implementation**: We use project name + environment, but account ID could be added.

## Resources That DON'T Need Account ID

These resources are unique within an account, so account ID is optional:

- **VPCs**: Unique per account/region
- **ECS Clusters**: Unique per account/region
- **RDS Instances**: Unique per account/region
- **SQS Queues**: Unique per account/region
- **Security Groups**: Unique per account/region
- **Subnets**: Unique per VPC

**However**, including account ID can still be beneficial for:
- Multi-account environments
- Resource identification in CloudTrail logs
- Cross-account resource sharing
- Avoiding confusion in multi-account setups

## Current Implementation Analysis

### ✅ Already Using Account ID

1. **S3 Buckets** (`storage.tf`):
   ```hcl
   bucket = "${var.project_name}-exports-${var.environment}-${data.aws_caller_identity.current.account_id}"
   ```

2. **Terraform State Bucket** (`iam_cicd.tf`):
   ```hcl
   bucket = "${var.project_name}-terraform-state-${var.environment}-${data.aws_caller_identity.current.account_id}"
   ```

### ❌ Not Using Account ID (But Could)

- VPCs, ECS clusters, RDS instances, SQS queues, etc.

## Recommendations

### Option 1: Minimal (Current Approach) ✅ Recommended for Most Cases

**Use account ID only where required:**
- S3 buckets (required)
- Terraform state bucket (good practice)

**Pros**:
- Simpler resource names
- Easier to read and manage
- Sufficient for single-account deployments

**Cons**:
- Less clear in multi-account environments
- Harder to identify resources in cross-account scenarios

### Option 2: Comprehensive (Multi-Account Strategy)

**Use account ID for all resources:**

```hcl
# Example for ECS cluster
name = "${var.project_name}-cluster-${var.environment}-${data.aws_caller_identity.current.account_id}"

# Example for RDS
identifier = "${var.project_name}-db-${var.environment}-${data.aws_caller_identity.current.account_id}"
```

**Pros**:
- Clear resource identification across accounts
- Better for multi-account strategies
- Easier cross-account resource sharing
- Better CloudTrail log readability

**Cons**:
- Longer resource names (may hit length limits)
- More verbose
- May require truncation for some resources

### Option 3: Hybrid (Recommended for Enterprise)

**Use account ID for:**
- ✅ S3 buckets (required)
- ✅ IAM roles (recommended)
- ✅ Terraform state (recommended)
- ✅ Resources shared across accounts
- ❌ Resources that are clearly account-scoped (VPCs, ECS clusters)

## AWS Resource Name Length Limits

Be aware of length limits when adding account IDs:

| Resource | Max Length | Example with Account ID |
|----------|------------|-------------------------|
| S3 Bucket | 63 chars | ✅ `import-export-orchestrator-exports-dev-123456789012` (50 chars) |
| ALB | 32 chars | ⚠️ May need truncation |
| Target Group | 32 chars | ⚠️ May need truncation |
| IAM Role | 64 chars | ✅ Usually fine |
| RDS Instance | 63 chars | ✅ Usually fine |
| ECS Cluster | 255 chars | ✅ No issue |
| SQS Queue | 80 chars | ✅ Usually fine |

## Best Practice Summary

### For Single-Account Deployments

✅ **Current approach is good**:
- Account ID for S3 buckets (required)
- Account ID for Terraform state (recommended)
- No account ID for other resources (optional)

### For Multi-Account Deployments

✅ **Consider adding account ID to**:
- IAM roles (for cross-account access)
- Resources shared between accounts
- Resources referenced in CloudFormation/CDK stacks

### General Guidelines

1. **Always include account ID for S3 buckets** (required)
2. **Consider account ID for IAM roles** (recommended for multi-account)
3. **Use environment/region in names** (already doing this ✅)
4. **Keep names descriptive but concise**
5. **Use consistent naming patterns** across all resources
6. **Document your naming convention** (this document)

## Example: Updated Naming Convention

If you want to add account ID to more resources:

```hcl
# Variables
variable "include_account_id" {
  description = "Include AWS account ID in resource names (useful for multi-account)"
  type        = bool
  default     = false
}

# Usage
locals {
  name_prefix = var.include_account_id ? 
    "${var.project_name}-${var.environment}-${data.aws_caller_identity.current.account_id}" :
    "${var.project_name}-${var.environment}"
}

# Then use in resources
resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"
}
```

## Conclusion

**For your current setup**: The existing approach is good! You're using account ID where it's required (S3) and where it's recommended (Terraform state). This is sufficient for most single-account deployments.

**If you plan to use multiple AWS accounts**: Consider adding account ID to IAM roles and any resources that will be shared or referenced across accounts.

