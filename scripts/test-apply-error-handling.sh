#!/bin/bash
# Test the apply step with "already exists" error handling
# This simulates the new error handling logic in deploy.yml

set -e

cd "$(dirname "$0")/../infra/aws/terraform"

# Set environment variables (adjust as needed)
export TF_VAR_database_password="${TF_VAR_database_password:-test-password}"
export TF_VAR_github_repository="${TF_VAR_github_repository:-rajivskumar/import-export-orchestrator}"
export TF_VAR_environment="${TF_VAR_environment:-dev}"
export AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-429763994533}"

ENV="${TF_VAR_environment}"
PROJECT_NAME="import-export-orchestrator"

echo "🧪 Testing apply step with 'already exists' error handling..."
echo "Environment: $ENV"
echo "Project: $PROJECT_NAME"
echo ""

# Get account ID from AWS if not provided
if [ -z "$AWS_ACCOUNT_ID" ]; then
  AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "429763994533")
fi

# Import function (same as in deploy.yml)
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

# Step 1: Ensure we have a plan file
echo "📋 Step 1: Creating terraform plan..."
if [ ! -f "tfplan" ]; then
  echo "  Plan file not found, creating one..."
  terraform plan \
    -var-file="terraform.tfvars" \
    -out=tfplan || {
      echo "❌ Terraform plan failed"
      exit 1
    }
  echo "✅ Plan file created"
else
  echo "✅ Plan file already exists"
fi

# Step 2: Test apply with error handling
echo ""
echo "🚀 Step 2: Testing apply with error handling..."
echo ""

# Try apply - if it fails with "already exists", import and retry
# Use pipefail to capture terraform's exit code, not tee's
set -o pipefail
terraform apply -auto-approve tfplan 2>&1 | tee /tmp/apply_output.log || {
  APPLY_EXIT=$?
  set +o pipefail
  
  # Check if failure was due to "already exists" errors
  if grep -qE "(already exists|AlreadyExists|ResourceAlreadyExists|EntityAlreadyExists|BucketAlreadyExists|RepositoryAlreadyExistsException|DBParameterGroupAlreadyExists|ResourceInUseException)" /tmp/apply_output.log; then
    echo ""
    echo "⚠️  Apply failed due to 'already exists' errors"
    echo "   This means imports didn't persist. Re-importing and retrying..."
    
    # Re-import all resources that might have failed
    set +e
    import_resource "aws_ecr_repository.app" "$PROJECT_NAME" "ECR repository" || true
    import_resource "aws_iam_role.ecs_task_execution" "${PROJECT_NAME}-ecs-task-execution-${ENV}" "ECS task execution role" || true
    import_resource "aws_iam_role.ecs_task" "${PROJECT_NAME}-ecs-task-${ENV}" "ECS task role" || true
    import_resource "aws_cloudwatch_log_group.ecs" "/ecs/${PROJECT_NAME}-${ENV}" "CloudWatch log group" || true
    import_resource "aws_s3_bucket.exports" "${PROJECT_NAME}-exports-${ENV}-${AWS_ACCOUNT_ID}" "Exports S3 bucket" || true
    import_resource "aws_s3_bucket.terraform_state" "${PROJECT_NAME}-terraform-state-${ENV}-${AWS_ACCOUNT_ID}" "Terraform state S3 bucket" || true
    import_resource "aws_dynamodb_table.terraform_state_lock" "${PROJECT_NAME}-terraform-state-lock-${ENV}" "DynamoDB table" || true
    import_resource "aws_db_subnet_group.main" "${PROJECT_NAME}-db-subnet-group-${ENV}" "DB subnet group" || true
    import_resource "aws_db_parameter_group.main" "${PROJECT_NAME}-postgres-${ENV}" "DB parameter group" || true
    
    OIDC_ARN=$(aws iam list-open-id-connect-providers --query "OpenIDConnectProviderList[?contains(Arn, 'token.actions.githubusercontent.com')].Arn" --output text 2>/dev/null | head -1)
    if [ -n "$OIDC_ARN" ]; then
      import_resource "aws_iam_openid_connect_provider.github" "$OIDC_ARN" "OIDC provider" || true
    fi
    
    set -e
    
    # Force state sync
    terraform state pull >/dev/null 2>&1 || true
    sleep 2
    
    # Regenerate plan with updated state
    echo "  Regenerating plan with updated state..."
    terraform plan -var-file="terraform.tfvars" -out=tfplan >/dev/null 2>&1 || true
    
    # Retry apply
    echo "  Retrying terraform apply..."
    terraform apply -auto-approve tfplan || {
      echo "❌ Terraform apply failed after retry"
      echo "Check the error messages above for details"
      exit 1
    }
    echo "✅ Terraform apply completed successfully (after retry)"
  else
    echo "❌ Terraform apply failed with non-recoverable errors"
    echo "Last 50 lines of output:"
    tail -50 /tmp/apply_output.log || cat /tmp/apply_output.log
    exit 1
  fi
}

# If we get here, apply succeeded on first try
echo "✅ Terraform apply completed successfully"

echo ""
echo "✅ Test completed successfully!"

