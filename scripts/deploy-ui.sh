#!/bin/bash
# Deploy UI to AWS S3 + CloudFront
# Usage: ./scripts/deploy-ui.sh [environment]
# Example: ./scripts/deploy-ui.sh dev

set -e

ENVIRONMENT="${1:-dev}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
UI_DIR="$PROJECT_ROOT/ui"
TERRAFORM_DIR="$PROJECT_ROOT/infra/aws/terraform"

echo "=========================================="
echo "Deploying UI to AWS ($ENVIRONMENT)"
echo "=========================================="

# Get terraform outputs
cd "$TERRAFORM_DIR"

UI_BUCKET=$(terraform output -raw ui_bucket_name 2>/dev/null || echo "")
CLOUDFRONT_ID=$(terraform output -raw cloudfront_distribution_id 2>/dev/null || echo "")
UI_URL=$(terraform output -raw ui_url 2>/dev/null || echo "")
ALB_URL=$(terraform output -raw alb_dns_name 2>/dev/null || echo "")

if [ -z "$UI_BUCKET" ]; then
    echo "Error: Could not get UI bucket name from terraform outputs."
    echo "Make sure you've run 'terraform apply' first."
    exit 1
fi

echo "UI Bucket: $UI_BUCKET"
echo "CloudFront Distribution: ${CLOUDFRONT_ID:-'(not available - using S3 website)'}"
echo "ALB URL: $ALB_URL"
echo ""

# Build the UI
echo "Step 1: Building UI..."
cd "$UI_DIR"

# Set API URL for production build
# If CloudFront is available, use /api (CloudFront proxies to ALB)
# If only S3, use direct ALB URL (requires CORS)
if [ -n "$CLOUDFRONT_ID" ]; then
    export VITE_API_URL="/api"
    echo "Using CloudFront proxy: /api"
else
    export VITE_API_URL="http://$ALB_URL"
    echo "Using direct ALB URL: http://$ALB_URL"
fi

npm ci --silent
npm run build

if [ ! -d "dist" ]; then
    echo "Error: Build failed - dist directory not found"
    exit 1
fi

echo "Build complete!"
echo ""

# Sync to S3
echo "Step 2: Syncing to S3..."
aws s3 sync dist/ "s3://$UI_BUCKET/" \
    --delete \
    --cache-control "public, max-age=31536000, immutable" \
    --exclude "index.html" \
    --exclude "*.json"

# Upload index.html and JSON files with no-cache
aws s3 cp dist/index.html "s3://$UI_BUCKET/index.html" \
    --cache-control "no-cache, no-store, must-revalidate"

# Upload any JSON files (like manifest) with shorter cache
find dist -name "*.json" -exec aws s3 cp {} "s3://$UI_BUCKET/{}" \
    --cache-control "public, max-age=0, must-revalidate" \; 2>/dev/null || true

echo "S3 sync complete!"
echo ""

# Invalidate CloudFront cache
if [ -n "$CLOUDFRONT_ID" ]; then
    echo "Step 3: Invalidating CloudFront cache..."
    INVALIDATION_ID=$(aws cloudfront create-invalidation \
        --distribution-id "$CLOUDFRONT_ID" \
        --paths "/*" \
        --query 'Invalidation.Id' \
        --output text)

    echo "Invalidation created: $INVALIDATION_ID"
    echo "Note: Cache invalidation may take a few minutes to complete."
else
    echo "Step 3: Skipping CloudFront invalidation (no distribution ID)"
fi

echo ""
echo "=========================================="
echo "Deployment complete!"
echo "=========================================="
echo ""
echo "UI URL: $UI_URL"
echo ""
echo "Note: If this is the first deployment, DNS propagation"
echo "may take a few minutes."
