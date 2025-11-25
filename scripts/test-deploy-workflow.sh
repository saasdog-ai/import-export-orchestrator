#!/bin/bash
# Test the deploy.yml workflow steps locally
# This simulates what GitHub Actions will do

set -e

cd "$(dirname "$0")/../infra/aws/terraform"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🧪 Testing Deploy Workflow Steps${NC}"
echo ""

# Check AWS credentials
if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo -e "${RED}❌ AWS credentials not configured${NC}"
  exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ENV="${TF_VAR_environment:-dev}"
GITHUB_REPO="${TF_VAR_github_repository:-rajivskumar/import-export-orchestrator}"

echo -e "${GREEN}✅ AWS Account: ${AWS_ACCOUNT_ID}${NC}"
echo -e "${GREEN}✅ Environment: ${ENV}${NC}"
echo -e "${GREEN}✅ GitHub Repo: ${GITHUB_REPO}${NC}"
echo ""

# Step 1: Check terraform.tfvars
echo -e "${YELLOW}📋 Step 1: Checking terraform.tfvars...${NC}"
if [ ! -f "terraform.tfvars" ]; then
  echo -e "${YELLOW}⚠️  terraform.tfvars not found${NC}"
  if [ -f "terraform.tfvars.example" ]; then
    echo "  Creating from example..."
    cp terraform.tfvars.example terraform.tfvars
    echo -e "${GREEN}✅ Created terraform.tfvars${NC}"
  else
    echo -e "${RED}❌ terraform.tfvars.example not found${NC}"
    exit 1
  fi
else
  echo -e "${GREEN}✅ terraform.tfvars exists${NC}"
fi

# Format terraform.tfvars
terraform fmt terraform.tfvars
echo ""

# Step 2: Terraform Init
echo -e "${YELLOW}📋 Step 2: Terraform Init...${NC}"
export TF_VAR_github_repository="${GITHUB_REPO}"
export TF_VAR_environment="${ENV}"
export AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID}"

terraform init \
  -backend-config="bucket=import-export-orchestrator-terraform-state-${ENV}-${AWS_ACCOUNT_ID}" \
  -backend-config="key=terraform.tfstate" \
  -backend-config="region=us-east-1" \
  -backend-config="encrypt=true" \
  -backend-config="dynamodb_table=import-export-orchestrator-terraform-state-lock-${ENV}"

echo -e "${GREEN}✅ Terraform initialized${NC}"
echo ""

# Step 3: Terraform Format Check
echo -e "${YELLOW}📋 Step 3: Terraform Format Check...${NC}"
if terraform fmt -check; then
  echo -e "${GREEN}✅ All Terraform files are properly formatted${NC}"
else
  echo -e "${RED}❌ Format check failed${NC}"
  echo "Run 'terraform fmt' to fix formatting issues"
  exit 1
fi
echo ""

# Step 4: Terraform Validate
echo -e "${YELLOW}📋 Step 4: Terraform Validate...${NC}"
if terraform validate; then
  echo -e "${GREEN}✅ Terraform configuration is valid${NC}"
else
  echo -e "${RED}❌ Terraform validation failed${NC}"
  exit 1
fi
echo ""

# Step 5: Terraform Plan
echo -e "${YELLOW}📋 Step 5: Terraform Plan...${NC}"
if [ -z "$TF_VAR_database_password" ]; then
  echo -e "${YELLOW}⚠️  TF_VAR_database_password not set${NC}"
  echo "  Setting a dummy password for plan (will fail on apply if not set)"
  export TF_VAR_database_password="dummy-for-plan-only"
fi

terraform plan -out=tfplan

if [ -f "tfplan" ]; then
  echo -e "${GREEN}✅ Terraform plan created successfully${NC}"
  PLAN_SIZE=$(du -h tfplan | cut -f1)
  echo "  Plan file size: ${PLAN_SIZE}"
else
  echo -e "${RED}❌ Terraform plan file not created${NC}"
  exit 1
fi
echo ""

# Step 6: Show what would be applied (dry run)
echo -e "${YELLOW}📋 Step 6: Plan Summary (dry run - not applying)...${NC}"
echo "The plan shows what would be created/changed/destroyed."
echo ""
echo "⚠️  This is a DRY RUN. No changes will be applied."
echo ""
echo "To actually apply, run:"
echo "  cd infra/aws/terraform"
echo "  terraform apply tfplan"
echo ""

# Cleanup
if [ "$TF_VAR_database_password" = "dummy-for-plan-only" ]; then
  unset TF_VAR_database_password
fi

echo -e "${GREEN}✅ Workflow test completed successfully!${NC}"
echo ""
echo "All workflow steps passed. The deploy.yml should work in GitHub Actions."

