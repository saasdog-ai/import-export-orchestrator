#!/bin/bash
# Helper script to run the deploy workflow locally using act
# 
# Prerequisites:
# - Docker must be running
# - AWS credentials configured (aws configure or AWS_PROFILE)
# - GitHub secrets set as environment variables or in .secrets file

set -e

cd "$(dirname "$0")/.."

echo "🚀 Running deploy workflow locally with act..."
echo ""

# Check if .secrets file exists (act can use this for secrets)
if [ ! -f .secrets ]; then
  echo "⚠️  No .secrets file found. Creating template..."
  cat > .secrets <<EOF
# GitHub Actions secrets for local testing
# Add your actual secrets here (this file is gitignored)
DATABASE_PASSWORD=your-database-password
AWS_ROLE_ARN=your-aws-role-arn
AWS_ACCOUNT_ID=429763994533
EOF
  echo "  Created .secrets template - please fill in your actual values"
  echo "  Then run this script again"
  exit 1
fi

# Check if required secrets are set
if ! grep -q "DATABASE_PASSWORD=" .secrets || grep -q "DATABASE_PASSWORD=your-database-password" .secrets; then
  echo "❌ Error: DATABASE_PASSWORD not set in .secrets file"
  echo "  Please edit .secrets and add your actual database password"
  exit 1
fi

echo "📋 Running deploy workflow..."
echo "  This will simulate the GitHub Actions workflow"
echo "  Note: Some steps may behave differently than in GitHub Actions"
echo ""

# Run the deploy workflow
# -W: workflow file
# --secret-file: use .secrets file for secrets
# -j: specific job to run
# --container-architecture: use linux/amd64 for compatibility
act workflow_dispatch \
  -W .github/workflows/deploy.yml \
  --secret-file .secrets \
  -j deploy \
  --container-architecture linux/amd64 \
  --env TF_VAR_environment=dev \
  --env TF_VAR_github_repository=rajivskumar/import-export-orchestrator

echo ""
echo "✅ Workflow completed!"

