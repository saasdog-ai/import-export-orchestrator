#!/bin/bash
# Script to rebuild Docker image and update ECS service
# This is useful after making changes to the Dockerfile or dependencies

set -e

cd "$(dirname "$0")/.."

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check AWS credentials
if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo -e "${RED}❌ AWS credentials not configured${NC}"
  exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="${AWS_REGION:-us-east-1}"
ENV="${TF_VAR_environment:-dev}"
PROJECT_NAME="import-export-orchestrator"
ECR_REPO="${PROJECT_NAME}"
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

echo -e "${GREEN}🐳 Rebuilding and deploying Docker image${NC}"
echo -e "  Account: ${AWS_ACCOUNT_ID}"
echo -e "  Region: ${AWS_REGION}"
echo -e "  Repository: ${ECR_REPO}"
echo -e "  Tag: ${IMAGE_TAG}"
echo ""

# Step 1: Login to ECR
echo -e "${YELLOW}📋 Step 1: Logging into ECR...${NC}"
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URI}
echo -e "${GREEN}✅ Logged into ECR${NC}"
echo ""

# Step 2: Build Docker image
echo -e "${YELLOW}📋 Step 2: Building Docker image...${NC}"
docker build -t ${ECR_REPO}:${IMAGE_TAG} .
echo -e "${GREEN}✅ Image built${NC}"
echo ""

# Step 3: Tag image
echo -e "${YELLOW}📋 Step 3: Tagging image...${NC}"
docker tag ${ECR_REPO}:${IMAGE_TAG} ${ECR_URI}:${IMAGE_TAG}
echo -e "${GREEN}✅ Image tagged${NC}"
echo ""

# Step 4: Push to ECR
echo -e "${YELLOW}📋 Step 4: Pushing to ECR...${NC}"
docker push ${ECR_URI}:${IMAGE_TAG}
echo -e "${GREEN}✅ Image pushed to ECR${NC}"
echo ""

# Step 5: Force ECS service update
echo -e "${YELLOW}📋 Step 5: Updating ECS service to use new image...${NC}"
CLUSTER_NAME="${PROJECT_NAME}-cluster-${ENV}"
SERVICE_NAME="${PROJECT_NAME}-service-${ENV}"

echo "  Cluster: ${CLUSTER_NAME}"
echo "  Service: ${SERVICE_NAME}"

# Force new deployment
aws ecs update-service \
  --cluster ${CLUSTER_NAME} \
  --service ${SERVICE_NAME} \
  --force-new-deployment \
  --region ${AWS_REGION} >/dev/null

echo -e "${GREEN}✅ ECS service update triggered${NC}"
echo ""

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo "The ECS service is now deploying the new image."
echo "You can monitor the deployment in the AWS Console or with:"
echo ""
echo "  aws ecs describe-services \\"
echo "    --cluster ${CLUSTER_NAME} \\"
echo "    --services ${SERVICE_NAME} \\"
echo "    --region ${AWS_REGION} \\"
echo "    --query 'services[0].deployments'"
echo ""

