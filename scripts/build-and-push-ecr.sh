#!/bin/bash
set -e

# Configuration
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-429763994533}"  # Default, override with env var
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REPO="import-export-orchestrator"
IMAGE_TAG="${1:-latest}"

ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}"

echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ECR_URI

echo "🏗️  Building Docker image..."
docker build -t $ECR_REPO:$IMAGE_TAG .

echo "🏷️  Tagging image..."
docker tag $ECR_REPO:$IMAGE_TAG $ECR_URI:$IMAGE_TAG

echo "📤 Pushing to ECR..."
docker push $ECR_URI:$IMAGE_TAG

echo "✅ Done! Image URI:"
echo "$ECR_URI:$IMAGE_TAG"
