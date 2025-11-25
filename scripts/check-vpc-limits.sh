#!/bin/bash
# Script to check VPC limits and list existing VPCs
# Helps diagnose VpcLimitExceeded errors

set -e

REGION="${AWS_REGION:-us-east-1}"

echo "🔍 Checking VPC limits and existing VPCs in ${REGION}..."
echo ""

# Get VPC limit
echo "=== VPC Limits ==="
VPC_LIMIT=$(aws service-quotas get-service-quota \
  --service-code ec2 \
  --quota-code L-0263D0A3 \
  --region ${REGION} \
  --query 'Quota.Value' \
  --output text 2>/dev/null || echo "5")  # Default limit is usually 5

echo "VPC Limit: ${VPC_LIMIT}"
echo ""

# Count existing VPCs
echo "=== Existing VPCs ==="
VPC_COUNT=$(aws ec2 describe-vpcs --region ${REGION} --query 'length(Vpcs)' --output text)
echo "Current VPC Count: ${VPC_COUNT}"
echo ""

if [ "${VPC_COUNT}" -ge "${VPC_LIMIT}" ]; then
  echo "⚠️  WARNING: You're at or over the VPC limit!"
  echo "   You need to either:"
  echo "   1. Delete unused VPCs, or"
  echo "   2. Use an existing VPC instead of creating a new one"
  echo ""
fi

# List all VPCs
echo "=== All VPCs in ${REGION} ==="
aws ec2 describe-vpcs \
  --region ${REGION} \
  --query 'Vpcs[*].[VpcId,CidrBlock,State,Tags[?Key==`Name`].Value|[0],IsDefault]' \
  --output table

echo ""
echo "💡 To delete an unused VPC:"
echo "   aws ec2 delete-vpc --vpc-id vpc-xxxxx --region ${REGION}"
echo ""
echo "💡 To use an existing VPC, modify vpc.tf to use a data source instead of creating a new VPC"
echo ""

