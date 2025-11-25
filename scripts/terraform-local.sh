#!/bin/bash
# Helper script to run Terraform locally
# This script helps you manage infrastructure from your local machine

set -e

cd "$(dirname "$0")/../infra/aws/terraform"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if AWS credentials are configured
if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo -e "${RED}❌ AWS credentials not configured${NC}"
  echo "Please run: aws configure"
  exit 1
fi

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✅ AWS Account: ${AWS_ACCOUNT_ID}${NC}"

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
  echo -e "${YELLOW}⚠️  terraform.tfvars not found. Creating from template...${NC}"
  cat > terraform.tfvars <<EOF
# Terraform Variables
project_name = "import-export-orchestrator"
environment  = "dev"
aws_region   = "us-east-1"

# Database
database_password = "CHANGE_ME"  # Set this to your database password

# ECS Configuration
ecs_desired_count = 1

# ALB Configuration
enable_alb = false

# GitHub Repository (for OIDC)
github_repository = "rajivskumar/import-export-orchestrator"
EOF
  echo -e "${YELLOW}⚠️  Please edit terraform.tfvars and set database_password${NC}"
  exit 1
fi

# Check if DATABASE_PASSWORD is set
if grep -q "CHANGE_ME" terraform.tfvars 2>/dev/null; then
  if [ -z "$TF_VAR_database_password" ]; then
    echo -e "${YELLOW}⚠️  database_password in terraform.tfvars is not set${NC}"
    echo "You can either:"
    echo "  1. Edit terraform.tfvars and set database_password"
    echo "  2. Export TF_VAR_database_password environment variable"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      exit 1
    fi
  fi
fi

# Check backend configuration
if grep -q "^# backend" main.tf; then
  echo -e "${YELLOW}ℹ️  Using local state (backend is commented out)${NC}"
  echo "   State will be stored in: terraform.tfstate"
else
  echo -e "${GREEN}ℹ️  Using remote state (S3 backend)${NC}"
fi

# Parse command
COMMAND="${1:-help}"

case "$COMMAND" in
  init)
    echo -e "${GREEN}🔧 Initializing Terraform...${NC}"
    terraform init
    ;;
  
  plan)
    echo -e "${GREEN}📋 Running terraform plan...${NC}"
    terraform plan -var-file="terraform.tfvars"
    ;;
  
  apply)
    echo -e "${GREEN}🚀 Applying Terraform changes...${NC}"
    terraform apply -var-file="terraform.tfvars"
    ;;
  
  destroy)
    echo -e "${RED}🗑️  Destroying infrastructure...${NC}"
    read -p "Are you sure you want to destroy all infrastructure? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
      echo "Cancelled"
      exit 1
    fi
    terraform destroy -var-file="terraform.tfvars"
    ;;
  
  recreate-ecs)
    echo -e "${GREEN}🔄 Recreating ECS tasks...${NC}"
    echo ""
    echo "This will:"
    echo "  1. Taint the ECS task definition (force recreation)"
    echo "  2. Taint the ECS service (force recreation)"
    echo "  3. Apply changes"
    echo ""
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      exit 1
    fi
    
    # Taint ECS task definition to force recreation
    echo "Tainting ECS task definition..."
    terraform taint aws_ecs_task_definition.main 2>/dev/null || echo "  (already tainted or doesn't exist)"
    
    # Taint ECS service to force recreation
    echo "Tainting ECS service..."
    terraform taint aws_ecs_service.main 2>/dev/null || echo "  (already tainted or doesn't exist)"
    
    # Apply changes
    echo ""
    echo "Applying changes..."
    terraform apply -var-file="terraform.tfvars"
    ;;
  
  state-list)
    echo -e "${GREEN}📋 Listing resources in state...${NC}"
    terraform state list
    ;;
  
  state-show)
    if [ -z "$2" ]; then
      echo -e "${RED}❌ Please specify a resource${NC}"
      echo "Usage: $0 state-show <resource>"
      echo "Example: $0 state-show aws_ecs_service.main"
      exit 1
    fi
    terraform state show "$2"
    ;;
  
  output)
    echo -e "${GREEN}📤 Terraform outputs:${NC}"
    terraform output
    ;;
  
  validate)
    echo -e "${GREEN}✅ Validating Terraform configuration...${NC}"
    terraform validate
    ;;
  
  fmt)
    echo -e "${GREEN}🎨 Formatting Terraform files...${NC}"
    terraform fmt -recursive
    ;;
  
  help|*)
    echo "Terraform Local Helper"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  init              Initialize Terraform"
    echo "  plan              Show what Terraform will do"
    echo "  apply             Apply Terraform changes"
    echo "  destroy           Destroy all infrastructure"
    echo "  recreate-ecs      Recreate ECS tasks and service"
    echo "  state-list        List all resources in state"
    echo "  state-show <res>  Show details of a resource"
    echo "  output            Show Terraform outputs"
    echo "  validate          Validate Terraform configuration"
    echo "  fmt               Format Terraform files"
    echo "  help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 init"
    echo "  $0 plan"
    echo "  $0 apply"
    echo "  $0 recreate-ecs"
    echo "  $0 state-show aws_ecs_service.main"
    ;;
esac

