#!/bin/bash
# Test the combined import, plan, and apply step locally
# This simulates what the GitHub Actions workflow does in one step

set -e

cd "$(dirname "$0")/../infra/aws/terraform"

# Set environment variables (adjust as needed)
export TF_VAR_database_password="${TF_VAR_database_password:-test-password}"
export TF_VAR_github_repository="${TF_VAR_github_repository:-rajivskumar/import-export-orchestrator}"
export TF_VAR_environment="${TF_VAR_environment:-dev}"
export AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-429763994533}"

ENV="${TF_VAR_environment}"
PROJECT_NAME="import-export-orchestrator"

echo "🧪 Testing combined import, plan, and apply step..."
echo "Environment: $ENV"
echo "Project: $PROJECT_NAME"
echo ""

# Step 1: Import existing resources
echo "🔍 Step 1: Attempting to import existing resources..."

# Get account ID from AWS if not provided
if [ -z "$AWS_ACCOUNT_ID" ]; then
  AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "429763994533")
fi

echo "Current state before imports:"
terraform state list 2>/dev/null | head -20 || echo "  (no resources in state yet - this is normal for first run)"
echo ""

# Import function
import_resource() {
  local resource=$1
  local id=$2
  local name=$3
  echo "  → Importing $name..."
  
  # Check if resource already exists in state
  if terraform state list 2>/dev/null | grep -q "^${resource}$"; then
    echo "    ✅ $name already in state, skipping"
    return 0
  fi
  
  # Import WITHOUT -target to ensure state is properly written
  local import_output
  import_output=$(terraform import -input=false -lock=false $resource "$id" 2>&1)
  local import_exit=$?
  
  # Check for success indicators
  local import_succeeded=false
  if echo "$import_output" | grep -qE "(Import prepared!|Refreshing state|aws_.*: Importing from ID)"; then
    import_succeeded=true
  fi
  
  if [ $import_exit -eq 0 ]; then
    import_succeeded=true
  fi
  
  # If import succeeded, verify it's in state
  if [ "$import_succeeded" = true ]; then
    if terraform state list 2>/dev/null | grep -q "^${resource}$"; then
      echo "    ✅ $name imported successfully"
      return 0
    fi
    
    if terraform state show "$resource" >/dev/null 2>&1; then
      echo "    ✅ $name imported successfully"
      return 0
    fi
    
    echo "    ✅ $name import completed"
    return 0
  fi
  
  # Check for validation errors
  if echo "$import_output" | grep -qE "(Error: Invalid count|Error: reading.*policy|Error: reading.*backups|Error: reading.*parameters)"; then
    if terraform state list 2>/dev/null | grep -q "^${resource}$" || terraform state show "$resource" >/dev/null 2>&1; then
      echo "    ✅ $name imported (validation errors ignored)"
      return 0
    fi
  fi
  
  # Import failed
  echo "    ⚠️  $name import failed"
  echo "    Exit code: $import_exit"
  echo "    Error: $(echo "$import_output" | grep -E "Error:" | head -1 || echo "Unknown error")"
  return 1
}

# Import resources
echo "Starting imports..."
echo ""

import_resource "aws_ecr_repository.app" "$PROJECT_NAME" "ECR repository"
import_resource "aws_iam_role.ecs_task_execution" "${PROJECT_NAME}-ecs-task-execution-${ENV}" "ECS task execution role"
import_resource "aws_iam_role.ecs_task" "${PROJECT_NAME}-ecs-task-${ENV}" "ECS task role"
import_resource "aws_cloudwatch_log_group.ecs" "/ecs/${PROJECT_NAME}-${ENV}" "CloudWatch log group"
import_resource "aws_s3_bucket.exports" "${PROJECT_NAME}-exports-${ENV}-${AWS_ACCOUNT_ID}" "Exports S3 bucket"
import_resource "aws_s3_bucket.terraform_state" "${PROJECT_NAME}-terraform-state-${ENV}-${AWS_ACCOUNT_ID}" "Terraform state S3 bucket"
import_resource "aws_dynamodb_table.terraform_state_lock" "${PROJECT_NAME}-terraform-state-lock-${ENV}" "DynamoDB table"
import_resource "aws_db_subnet_group.main" "${PROJECT_NAME}-db-subnet-group-${ENV}" "DB subnet group"
import_resource "aws_db_parameter_group.main" "${PROJECT_NAME}-postgres-${ENV}" "DB parameter group"

# Import OIDC provider
echo "  → Checking for OIDC provider..."
OIDC_ARN=$(aws iam list-open-id-connect-providers --query "OpenIDConnectProviderList[?contains(Arn, 'token.actions.githubusercontent.com')].Arn" --output text 2>/dev/null | head -1)
if [ -n "$OIDC_ARN" ]; then
  import_resource "aws_iam_openid_connect_provider.github" "$OIDC_ARN" "OIDC provider"
else
  echo "    ⚠️  OIDC provider not found, will be created"
fi

# Verify what was actually imported
echo ""
echo "📊 Final state after imports:"
terraform state list 2>/dev/null | head -30 || echo "  (no resources in state)"

IMPORTED_COUNT=$(terraform state list 2>/dev/null | wc -l || echo "0")
echo "  Total resources in state: $IMPORTED_COUNT"

# List the specific resources we tried to import
echo ""
echo "📋 Checking imported resources:"
for resource in "aws_ecr_repository.app" "aws_iam_role.ecs_task_execution" "aws_iam_role.ecs_task" "aws_cloudwatch_log_group.ecs" "aws_s3_bucket.exports" "aws_s3_bucket.terraform_state" "aws_dynamodb_table.terraform_state_lock" "aws_db_subnet_group.main" "aws_db_parameter_group.main"; do
  if terraform state list 2>/dev/null | grep -q "^${resource}$"; then
    echo "  ✅ $resource"
  else
    echo "  ❌ $resource (NOT in state)"
  fi
done

echo ""
echo "✅ Import step completed"

# Step 2: Run terraform plan
echo ""
echo "🔍 Step 2: Running terraform plan..."
terraform plan \
  -var-file="terraform.tfvars" \
  -out=tfplan || {
    echo "❌ Terraform plan failed"
    echo "Checking for common issues..."
    terraform validate || echo "Validation failed"
    exit 1
  }
echo "✅ Terraform plan completed successfully"

# Step 3: Show what would be applied (but don't actually apply)
echo ""
echo "📋 Step 3: Plan summary (dry-run, not applying):"
echo "The plan shows what would be created/changed/destroyed."
echo ""
echo "✅ Plan file saved to: infra/aws/terraform/tfplan"
echo ""
echo "To actually apply, run:"
echo "  cd infra/aws/terraform"
echo "  terraform apply tfplan"
echo ""
echo "⚠️  Note: This script does NOT run 'terraform apply' for safety."
echo "    In GitHub Actions, it will apply automatically on main branch."

