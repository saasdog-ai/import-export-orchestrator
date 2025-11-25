#!/bin/bash
# Test script to simulate GitHub Actions deploy.yml workflow locally
# This tests the key steps without needing GitHub Actions or OIDC

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="${SCRIPT_DIR}/../infra/aws/terraform"
ENVIRONMENT="${ENVIRONMENT:-dev}"
ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo '429763994533')}"

echo "🧪 Testing deploy.yml workflow steps locally..."
echo "Environment: ${ENVIRONMENT}"
echo "Account ID: ${ACCOUNT_ID}"
echo ""

cd "${TERRAFORM_DIR}"

# Step 1: Create terraform.tfvars from example (if needed)
echo "📝 Step 1: Create terraform.tfvars from example"
if [ ! -f terraform.tfvars ]; then
  echo "Creating terraform.tfvars from example..."
  cp terraform.tfvars.example terraform.tfvars
  echo "✅ Created terraform.tfvars"
else
  echo "✅ terraform.tfvars already exists"
fi
terraform fmt terraform.tfvars
echo ""

# Step 2: Terraform Init with backend
echo "📝 Step 2: Terraform Init with backend"
export TF_VAR_github_repository="test/test"
export TF_VAR_environment="${ENVIRONMENT}"

terraform init \
  -backend-config="bucket=import-export-orchestrator-terraform-state-${ENVIRONMENT}-${ACCOUNT_ID}" \
  -backend-config="key=terraform.tfstate" \
  -backend-config="region=us-east-1" \
  -backend-config="encrypt=true" \
  -backend-config="dynamodb_table=import-export-orchestrator-terraform-state-lock-${ENVIRONMENT}"

if [ $? -eq 0 ]; then
  echo "✅ Terraform init successful"
else
  echo "❌ Terraform init failed"
  exit 1
fi
echo ""

# Step 3: Terraform Format Check
echo "📝 Step 3: Terraform Format Check"
if terraform fmt -check; then
  echo "✅ All Terraform files are properly formatted"
else
  echo "❌ Format check failed for .tf files"
  echo "Run 'terraform fmt' to fix formatting issues"
  exit 1
fi
echo ""

# Step 4: Terraform Validate
echo "📝 Step 4: Terraform Validate"
if terraform validate; then
  echo "✅ Terraform validation successful"
else
  echo "❌ Terraform validation failed"
  exit 1
fi
echo ""

# Step 5: Terraform Plan
echo "📝 Step 5: Terraform Plan"
export TF_VAR_database_password="${DATABASE_PASSWORD:-test-password-123}"

if terraform plan -out=tfplan; then
  echo "✅ Terraform plan successful"
  echo ""
  echo "📋 Plan Summary:"
  terraform show -json tfplan | jq -r '.resource_changes[] | "\(.type) \(.name): \(.change.actions[])"' 2>/dev/null || terraform show tfplan | grep -E "^Plan:|to add|to change|to destroy" || echo "   (Plan details available in tfplan file)"
else
  echo "❌ Terraform plan failed"
  exit 1
fi
echo ""

echo "✅ All workflow steps completed successfully!"
echo ""
echo "Note: This test skipped the 'Terraform Apply' step for safety."
echo "To apply changes, run: terraform apply tfplan"
echo ""
