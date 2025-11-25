#!/bin/bash
# Script to start ECS tasks or ensure the ECS service is running tasks

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Default values
ENV="${TF_VAR_environment:-dev}"
PROJECT_NAME="import-export-orchestrator"
CLUSTER_NAME="${PROJECT_NAME}-cluster-${ENV}"
SERVICE_NAME="${PROJECT_NAME}-service-${ENV}"
AWS_REGION="${AWS_REGION:-us-east-1}"

echo -e "${GREEN}🚀 Starting ECS Tasks${NC}"
echo -e "  Cluster: ${CLUSTER_NAME}"
echo -e "  Service: ${SERVICE_NAME}"
echo -e "  Region: ${AWS_REGION}"
echo ""

# Check AWS credentials
if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo -e "${RED}❌ AWS credentials not configured${NC}"
  exit 1
fi

# Check if service exists
echo -e "${YELLOW}📋 Checking ECS service status...${NC}"
SERVICE_INFO=$(aws ecs describe-services \
  --cluster ${CLUSTER_NAME} \
  --services ${SERVICE_NAME} \
  --region ${AWS_REGION} 2>&1)

if echo "$SERVICE_INFO" | grep -q "ServiceNotFoundException"; then
  echo -e "${RED}❌ ECS service '${SERVICE_NAME}' not found${NC}"
  echo ""
  echo "The service might not exist yet. You can:"
  echo "  1. Create it using Terraform: ./scripts/terraform-local.sh apply"
  echo "  2. Or check if the service name is different"
  exit 1
fi

# Get current service status
DESIRED_COUNT=$(echo "$SERVICE_INFO" | jq -r '.services[0].desiredCount // 0')
RUNNING_COUNT=$(echo "$SERVICE_INFO" | jq -r '.services[0].runningCount // 0')
PENDING_COUNT=$(echo "$SERVICE_INFO" | jq -r '.services[0].pendingCount // 0')

echo -e "  Desired tasks: ${DESIRED_COUNT}"
echo -e "  Running tasks: ${RUNNING_COUNT}"
echo -e "  Pending tasks: ${PENDING_COUNT}"
echo ""

# If desired count is 0, update it to 1
if [ "$DESIRED_COUNT" -eq 0 ]; then
  echo -e "${YELLOW}⚠️  Service desired count is 0. Updating to 1...${NC}"
  aws ecs update-service \
    --cluster ${CLUSTER_NAME} \
    --service ${SERVICE_NAME} \
    --desired-count 1 \
    --region ${AWS_REGION} >/dev/null
  echo -e "${GREEN}✅ Service updated. Desired count set to 1${NC}"
  echo ""
  echo "The service will start tasks automatically. This may take a few minutes."
  echo ""
  echo "You can monitor the service with:"
  echo "  aws ecs describe-services --cluster ${CLUSTER_NAME} --services ${SERVICE_NAME} --region ${AWS_REGION}"
  exit 0
fi

# If there are no running tasks but desired count > 0, check what's wrong
if [ "$RUNNING_COUNT" -eq 0 ] && [ "$DESIRED_COUNT" -gt 0 ]; then
  echo -e "${YELLOW}⚠️  No tasks are running but desired count is ${DESIRED_COUNT}${NC}"
  echo ""
  echo "Checking task definitions and recent task failures..."
  
  # Get recent task failures
  TASK_FAILURES=$(aws ecs list-tasks \
    --cluster ${CLUSTER_NAME} \
    --service-name ${SERVICE_NAME} \
    --desired-status STOPPED \
    --region ${AWS_REGION} 2>/dev/null | jq -r '.taskArns[]' | head -5)
  
  if [ -n "$TASK_FAILURES" ]; then
    echo ""
    echo "Recent stopped tasks:"
    for TASK_ARN in $TASK_FAILURES; do
      TASK_DETAILS=$(aws ecs describe-tasks \
        --cluster ${CLUSTER_NAME} \
        --tasks ${TASK_ARN} \
        --region ${AWS_REGION} 2>/dev/null)
      
      STOPPED_REASON=$(echo "$TASK_DETAILS" | jq -r '.tasks[0].stoppedReason // "Unknown"')
      EXIT_CODE=$(echo "$TASK_DETAILS" | jq -r '.tasks[0].containers[0].exitCode // "N/A"')
      
      echo -e "  ${RED}Task: ${TASK_ARN}${NC}"
      echo -e "    Reason: ${STOPPED_REASON}"
      echo -e "    Exit Code: ${EXIT_CODE}"
    done
  fi
  
  echo ""
  echo "Options:"
  echo "  1. Force a new deployment:"
  echo "     aws ecs update-service --cluster ${CLUSTER_NAME} --service ${SERVICE_NAME} --force-new-deployment --region ${AWS_REGION}"
  echo ""
  echo "  2. Check CloudWatch logs for errors"
  echo ""
  echo "  3. Manually run a task (see below)"
  
  # Ask if user wants to force new deployment
  read -p "Force a new deployment now? (y/N) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${YELLOW}🔄 Forcing new deployment...${NC}"
    aws ecs update-service \
      --cluster ${CLUSTER_NAME} \
      --service ${SERVICE_NAME} \
      --force-new-deployment \
      --region ${AWS_REGION} >/dev/null
    echo -e "${GREEN}✅ New deployment triggered${NC}"
    echo ""
    echo "The service will start new tasks. This may take a few minutes."
  fi
  
  exit 0
fi

# If tasks are running, show status
if [ "$RUNNING_COUNT" -gt 0 ]; then
  echo -e "${GREEN}✅ ${RUNNING_COUNT} task(s) are running${NC}"
  echo ""
  echo "Running tasks:"
  TASK_ARNS=$(aws ecs list-tasks \
    --cluster ${CLUSTER_NAME} \
    --service-name ${SERVICE_NAME} \
    --desired-status RUNNING \
    --region ${AWS_REGION} 2>/dev/null | jq -r '.taskArns[]')
  
  for TASK_ARN in $TASK_ARNS; do
    TASK_ID=$(echo "$TASK_ARN" | awk -F'/' '{print $NF}')
    echo -e "  ${GREEN}Task: ${TASK_ID}${NC}"
  done
  exit 0
fi

# If we get here, something unexpected happened
echo -e "${YELLOW}⚠️  Unexpected state. Desired: ${DESIRED_COUNT}, Running: ${RUNNING_COUNT}, Pending: ${PENDING_COUNT}${NC}"
echo ""
echo "You can manually start a task with:"
echo ""
echo "  # Get task definition"
echo "  TASK_DEF=\$(aws ecs describe-services --cluster ${CLUSTER_NAME} --services ${SERVICE_NAME} --region ${AWS_REGION} --query 'services[0].taskDefinition' --output text)"
echo ""
echo "  # Get subnet and security group"
echo "  SUBNET=\$(aws ec2 describe-subnets --filters \"Name=tag:Name,Values=*private*\" --query 'Subnets[0].SubnetId' --output text --region ${AWS_REGION})"
echo "  SG=\$(aws ec2 describe-security-groups --filters \"Name=tag:Name,Values=*ecs-tasks*\" --query 'SecurityGroups[0].GroupId' --output text --region ${AWS_REGION})"
echo ""
echo "  # Run task"
echo "  aws ecs run-task \\"
echo "    --cluster ${CLUSTER_NAME} \\"
echo "    --task-definition \${TASK_DEF} \\"
echo "    --launch-type FARGATE \\"
echo "    --network-configuration \"awsvpcConfiguration={subnets=[\${SUBNET}],securityGroups=[\${SG}],assignPublicIp=DISABLED}\" \\"
echo "    --region ${AWS_REGION}"

