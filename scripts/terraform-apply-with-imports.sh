#!/bin/bash
# Script to import existing AWS resources into Terraform state, then apply
# This handles the case where resources exist in AWS but not in Terraform state

set -e

cd "$(dirname "$0")/../infra/aws/terraform"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Terraform Apply with Automatic Imports${NC}"
echo ""

# Check AWS credentials
if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo -e "${RED}❌ AWS credentials not configured${NC}"
  exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ENV="${TF_VAR_environment:-dev}"
PROJECT_NAME="import-export-orchestrator"

echo -e "${GREEN}✅ AWS Account: ${AWS_ACCOUNT_ID}${NC}"
echo -e "${GREEN}✅ Environment: ${ENV}${NC}"
echo ""

# Function to import a resource if it exists in AWS but not in state
import_if_missing() {
  local resource=$1
  local id=$2
  local name=$3
  
  # Check if resource is already in state
  if terraform state list 2>/dev/null | grep -q "^${resource}$"; then
    echo -e "  ✅ ${name} already in state"
    return 0
  fi
  
  # Try to import
  echo -e "  → Importing ${name}..."
  if terraform import -input=false -lock=false "$resource" "$id" >/dev/null 2>&1; then
    echo -e "  ${GREEN}✅ ${name} imported${NC}"
    return 0
  else
    # Check if resource actually exists in AWS
    echo -e "  ${YELLOW}⚠️  ${name} not found or import failed (will be created if needed)${NC}"
    return 1
  fi
}

echo -e "${YELLOW}📋 Step 1: Importing existing resources (if any)...${NC}"
echo ""

# Import resources that commonly exist
set +e  # Don't exit on import errors
import_if_missing "aws_ecr_repository.app" "$PROJECT_NAME" "ECR repository"
import_if_missing "aws_iam_role.ecs_task_execution" "${PROJECT_NAME}-ecs-task-execution-${ENV}" "ECS task execution role"
import_if_missing "aws_iam_role.ecs_task" "${PROJECT_NAME}-ecs-task-${ENV}" "ECS task role"
import_if_missing "aws_cloudwatch_log_group.ecs" "/ecs/${PROJECT_NAME}-${ENV}" "CloudWatch log group"
import_if_missing "aws_s3_bucket.exports" "${PROJECT_NAME}-exports-${ENV}-${AWS_ACCOUNT_ID}" "Exports S3 bucket"
import_if_missing "aws_s3_bucket.terraform_state" "${PROJECT_NAME}-terraform-state-${ENV}-${AWS_ACCOUNT_ID}" "Terraform state S3 bucket"
import_if_missing "aws_dynamodb_table.terraform_state_lock" "${PROJECT_NAME}-terraform-state-lock-${ENV}" "DynamoDB table"
import_if_missing "aws_db_subnet_group.main" "${PROJECT_NAME}-db-subnet-group-${ENV}" "DB subnet group"
import_if_missing "aws_db_parameter_group.main" "${PROJECT_NAME}-postgres-${ENV}" "DB parameter group"

# Import OIDC provider if it exists
OIDC_ARN=$(aws iam list-open-id-connect-providers --query "OpenIDConnectProviderList[?contains(Arn, 'token.actions.githubusercontent.com')].Arn" --output text 2>/dev/null | head -1)
if [ -n "$OIDC_ARN" ]; then
  import_if_missing "aws_iam_openid_connect_provider.github" "$OIDC_ARN" "OIDC provider"
fi

set -e  # Re-enable error handling

echo ""
echo -e "${YELLOW}📋 Step 2: Running terraform plan...${NC}"
echo ""

# Run plan to see what will be created/updated
terraform plan -var-file="terraform.tfvars" -out=tfplan || {
  echo -e "${RED}❌ Terraform plan failed${NC}"
  exit 1
}

echo ""
echo -e "${YELLOW}📋 Step 3: Applying changes...${NC}"
echo ""

# Apply changes
terraform apply tfplan || {
  echo ""
  echo -e "${RED}❌ Terraform apply failed${NC}"
  echo ""
  echo "If you see 'already exists' errors, those resources need to be imported."
  echo "Run this script again - it will import them automatically."
  exit 1
}

echo ""
echo -e "${GREEN}✅ Terraform apply completed successfully!${NC}"
echo ""
echo "📤 Outputs:"
terraform output

