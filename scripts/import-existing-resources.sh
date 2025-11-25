#!/bin/bash
# Script to import existing AWS resources into Terraform state
# Run this ONCE locally after creating the bootstrap resources
# This should be run from the terraform directory: infra/aws/terraform

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="${SCRIPT_DIR}/../infra/aws/terraform"

cd "${TERRAFORM_DIR}"

echo "🔍 Importing existing AWS resources into Terraform state..."
echo ""

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ENVIRONMENT="${ENVIRONMENT:-dev}"
PROJECT_NAME="${PROJECT_NAME:-import-export-orchestrator}"

echo "Using:"
echo "  Account ID: ${ACCOUNT_ID}"
echo "  Environment: ${ENVIRONMENT}"
echo "  Project: ${PROJECT_NAME}"
echo ""

# Check if terraform is initialized
if [ ! -d ".terraform" ]; then
  echo "⚠️  Terraform not initialized. Running terraform init..."
  terraform init
  echo ""
fi

# Function to import a resource with error handling
import_resource() {
  local resource_type=$1
  local resource_name=$2
  local aws_id=$3
  
  echo "📦 Importing ${resource_type}.${resource_name}..."
  if terraform import "${resource_type}.${resource_name}" "${aws_id}" 2>/dev/null; then
    echo "   ✅ Success"
  else
    echo "   ⚠️  Failed or already imported (this is OK)"
  fi
  echo ""
}

# ECR Repository
echo "=== ECR Resources ==="
import_resource "aws_ecr_repository.app" "app" "${PROJECT_NAME}"

# CloudWatch Log Group
echo "=== CloudWatch Resources ==="
import_resource "aws_cloudwatch_log_group.ecs" "ecs" "/ecs/${PROJECT_NAME}-${ENVIRONMENT}"

# IAM Roles
echo "=== IAM Resources ==="
import_resource "aws_iam_role.ecs_task_execution" "ecs_task_execution" "${PROJECT_NAME}-ecs-task-execution-${ENVIRONMENT}"
import_resource "aws_iam_role.ecs_task" "ecs_task" "${PROJECT_NAME}-ecs-task-${ENVIRONMENT}"
import_resource "aws_iam_role.cicd" "cicd" "${PROJECT_NAME}-cicd-role-${ENVIRONMENT}"

# S3 Bucket for Exports
echo "=== S3 Resources ==="
EXPORTS_BUCKET="${PROJECT_NAME}-exports-${ENVIRONMENT}-${ACCOUNT_ID}"
import_resource "aws_s3_bucket.exports" "exports" "${EXPORTS_BUCKET}"

# RDS Parameter Group
echo "=== RDS Resources ==="
PARAM_GROUP_NAME="${PROJECT_NAME}-postgres-${ENVIRONMENT}"
import_resource "aws_db_parameter_group.main" "main" "${PARAM_GROUP_NAME}"

# Note: VPC and related resources should be checked separately
echo "=== VPC Resources ==="
echo "⚠️  VPC resources may need special handling if you hit VPC limits"
echo "   Check if VPC already exists:"
echo "   aws ec2 describe-vpcs --filters \"Name=tag:Name,Values=${PROJECT_NAME}-vpc-${ENVIRONMENT}\""
echo ""

echo "✅ Import process complete!"
echo ""
echo "Next steps:"
echo "1. Run 'terraform plan' to verify imports"
echo "2. Fix any issues shown in the plan"
echo "3. Once plan shows no unexpected changes, you're ready for CI/CD"
echo ""

