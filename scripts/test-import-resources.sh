#!/bin/bash
# Test script to verify resource imports work locally
# This simulates what the GitHub Actions workflow does
#
# Usage: ./scripts/test-import-resources.sh [environment]
# Example: ./scripts/test-import-resources.sh dev
#
# Required environment variables:
#   - TF_VAR_database_password (or set in terraform.tfvars)
#   - AWS credentials configured (aws configure or AWS_PROFILE)

# Don't exit on error - we want to test all imports even if some fail
set +e

cd "$(dirname "$0")/../infra/aws/terraform"

# Check for required environment variables
if [ -z "$TF_VAR_database_password" ]; then
  echo "⚠️  Warning: TF_VAR_database_password not set"
  echo "   You can set it with: export TF_VAR_database_password='your-password'"
  echo "   Or it will be read from terraform.tfvars if present"
  echo ""
fi

echo "🔍 Testing import of existing resources..."
echo ""

# Get account ID from AWS
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
if [ -z "$AWS_ACCOUNT_ID" ]; then
  echo "❌ Error: Could not get AWS account ID. Make sure AWS CLI is configured."
  exit 1
fi

echo "AWS Account ID: $AWS_ACCOUNT_ID"
echo ""

# Set environment
ENV="${1:-dev}"
PROJECT_NAME="import-export-orchestrator"

echo "Environment: $ENV"
echo "Project: $PROJECT_NAME"
echo ""

# Check if terraform.tfvars exists
if [ ! -f terraform.tfvars ]; then
  echo "Creating terraform.tfvars from example..."
  cp terraform.tfvars.example terraform.tfvars
  terraform fmt terraform.tfvars
fi

# Initialize Terraform
echo "Initializing Terraform..."
terraform init >/dev/null 2>&1 || terraform init

# Detect timeout command (macOS doesn't have timeout by default)
TIMEOUT_CMD=""
if command -v timeout >/dev/null 2>&1; then
  TIMEOUT_CMD="timeout 15"
elif command -v gtimeout >/dev/null 2>&1; then
  TIMEOUT_CMD="gtimeout 15"
fi

# Function to import with better error handling
import_resource() {
  local resource=$1
  local id=$2
  local name=$3
  echo "  → Importing $name..."
  
  # Check if resource already exists in state (ignore "No state file" errors)
  if terraform state list 2>/dev/null | grep -q "^${resource}$"; then
    echo "    ✅ $name already in state, skipping"
    return 0
  fi
  
  # Use -target to avoid validating entire configuration during import
  # Use -input=false to prevent prompts
  local import_output
  if [ -n "$TIMEOUT_CMD" ]; then
    import_output=$($TIMEOUT_CMD terraform import -target=$resource -input=false $resource "$id" 2>&1)
  else
    # No timeout available, just run the command
    import_output=$(terraform import -target=$resource -input=false $resource "$id" 2>&1)
  fi
  local import_exit=$?
  
  # Check if import succeeded by looking for success indicators in output
  # Even if Terraform exits with error due to validation, the import may have succeeded
  if echo "$import_output" | grep -qE "(Import prepared!|Refreshing state|Import successful)"; then
    # Verify resource is actually in state
    if terraform state list 2>/dev/null | grep -q "^${resource}$"; then
      echo "    ✅ $name imported successfully"
      return 0
    fi
  fi
  
  # If exit code is 0, import definitely succeeded
  if [ $import_exit -eq 0 ]; then
    echo "    ✅ $name imported successfully"
    return 0
  fi
  
  # Check if resource is in state despite error (validation errors don't prevent import)
  if terraform state list 2>/dev/null | grep -q "^${resource}$"; then
    echo "    ✅ $name imported (validation errors ignored)"
    return 0
  fi
  
  # Check for validation errors that occur after successful import
  if echo "$import_output" | grep -qE "(Error: Invalid count|Error: reading.*policy|Error: reading.*backups|Error: reading.*parameters)"; then
    # These are validation errors that don't prevent import - verify resource is in state
    if terraform state list 2>/dev/null | grep -q "^${resource}$"; then
      echo "    ✅ $name imported (validation errors ignored)"
      return 0
    fi
  fi
  
  echo "    ⚠️  $name import failed: $(echo "$import_output" | grep -E "Error:" | head -1 || echo "Unknown error")"
  echo "    Full error:"
  echo "$import_output" | head -5 | sed 's/^/      /'
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

echo ""
echo "✅ Import test completed!"
echo ""
echo "To verify, run: terraform state list"

