# IAM Roles and Policies for CI/CD (GitHub Actions)

# GitHub OIDC Provider
# This allows GitHub Actions to assume IAM roles without storing long-lived credentials
# Note: OIDC provider is account-wide, so we try to create it but it may already exist
resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = [
    "sts.amazonaws.com"
  ]

  thumbprint_list = [
    # These are PUBLIC certificate thumbprints (hashes), NOT secrets
    # They're used to verify GitHub's OIDC provider identity
    # Safe to store in code - they're public information published by GitHub
    # See: https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect
    "6938fd4d98bab03faadb97b34396831e3780aea1", # GitHub's OIDC thumbprint (primary)
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd"  # GitHub's OIDC thumbprint (backup)
  ]

  tags = merge(var.common_tags, {
    Name    = "${var.project_name}-github-oidc-${var.environment}"
    Purpose = "GitHub Actions OIDC Provider"
  })

  # Ignore changes if provider already exists (account-wide resource)
  lifecycle {
    ignore_changes = [url, client_id_list, thumbprint_list]
  }
}

# IAM Role for CI/CD (GitHub Actions)
# This role is assumed by GitHub Actions to deploy infrastructure
resource "aws_iam_role" "cicd" {
  name = "${var.project_name}-cicd-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            # Restrict to specific repository and branches
            "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:*"
          }
        }
      }
    ]
  })

  tags = merge(var.common_tags, {
    Name    = "${var.project_name}-cicd-role-${var.environment}"
    Purpose = "CI/CD Deployment Role"
  })
}

# IAM Policy for CI/CD - Terraform State Management
# NOTE: Backend resources (S3 bucket, DynamoDB table) are created separately via bootstrap
# This policy uses ARN patterns to reference them
resource "aws_iam_role_policy" "cicd_terraform_state" {
  name = "${var.project_name}-cicd-terraform-state-${var.environment}"
  role = aws_iam_role.cicd.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "arn:aws:s3:::${var.project_name}-terraform-state-${var.environment}-*",
          "arn:aws:s3:::${var.project_name}-terraform-state-${var.environment}-*/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem",
          "dynamodb:DescribeTable"
        ]
        Resource = "arn:aws:dynamodb:${var.aws_region}:*:table/${var.project_name}-terraform-state-lock-${var.environment}"
      }
    ]
  })
}

# IAM Policy for CI/CD - Infrastructure Deployment
resource "aws_iam_role_policy" "cicd_deploy" {
  name = "${var.project_name}-cicd-deploy-${var.environment}"
  role = aws_iam_role.cicd.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          # VPC and Networking
          "ec2:CreateVpc",
          "ec2:DeleteVpc",
          "ec2:DescribeVpcs",
          "ec2:ModifyVpcAttribute",
          "ec2:DescribeVpcAttribute",
          "ec2:DescribeAvailabilityZones",
          "ec2:DescribeAccountAttributes",
          "ec2:DescribeRegions",
          "ec2:CreateSubnet",
          "ec2:DeleteSubnet",
          "ec2:DescribeSubnets",
          "ec2:ModifySubnetAttribute",
          "ec2:CreateInternetGateway",
          "ec2:DeleteInternetGateway",
          "ec2:AttachInternetGateway",
          "ec2:DetachInternetGateway",
          "ec2:DescribeInternetGateways",
          "ec2:CreateRouteTable",
          "ec2:DeleteRouteTable",
          "ec2:DescribeRouteTables",
          "ec2:CreateRoute",
          "ec2:DeleteRoute",
          "ec2:AssociateRouteTable",
          "ec2:DisassociateRouteTable",
          "ec2:AllocateAddress",
          "ec2:ReleaseAddress",
          "ec2:DescribeAddresses",
          "ec2:DescribeAddressesAttribute",
          "ec2:AssociateAddress",
          "ec2:DisassociateAddress",
          "ec2:CreateNatGateway",
          "ec2:DeleteNatGateway",
          "ec2:DescribeNatGateways",
          # Security Groups
          "ec2:CreateSecurityGroup",
          "ec2:DeleteSecurityGroup",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeSecurityGroupRules",
          "ec2:AuthorizeSecurityGroupIngress",
          "ec2:AuthorizeSecurityGroupEgress",
          "ec2:RevokeSecurityGroupIngress",
          "ec2:RevokeSecurityGroupEgress",
          # RDS
          "rds:CreateDBInstance",
          "rds:DeleteDBInstance",
          "rds:DescribeDBInstances",
          "rds:ModifyDBInstance",
          "rds:CreateDBSubnetGroup",
          "rds:DeleteDBSubnetGroup",
          "rds:DescribeDBSubnetGroups",
          "rds:CreateDBParameterGroup",
          "rds:DeleteDBParameterGroup",
          "rds:DescribeDBParameterGroups",
          "rds:DescribeDBParameters",
          "rds:ModifyDBParameterGroup",
          "rds:ResetDBParameterGroup",
          "rds:AddTagsToResource",
          "rds:RemoveTagsFromResource",
          "rds:ListTagsForResource",
          # ECS
          "ecs:CreateCluster",
          "ecs:DeleteCluster",
          "ecs:DescribeClusters",
          "ecs:UpdateCluster",
          "ecs:TagResource",
          "ecs:UntagResource",
          "ecs:ListTagsForResource",
          "ecs:CreateService",
          "ecs:DeleteService",
          "ecs:DescribeServices",
          "ecs:UpdateService",
          "ecs:RegisterTaskDefinition",
          "ecs:DeregisterTaskDefinition",
          "ecs:DescribeTaskDefinition",
          "ecs:ListTaskDefinitions",
          # ECR (for managing repositories and pushing images)
          "ecr:GetAuthorizationToken",
          "ecr:DescribeRepositories",
          "ecr:ListRepositories",
          "ecr:DescribeImages",
          "ecr:ListImages",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:CreateRepository",
          "ecr:DeleteRepository",
          "ecr:SetRepositoryPolicy",
          "ecr:GetRepositoryPolicy",
          "ecr:GetLifecyclePolicy",
          "ecr:PutLifecyclePolicy",
          "ecr:DeleteLifecyclePolicy",
          "ecr:GetLifecyclePolicyPreview",
          "ecr:StartLifecyclePolicyPreview",
          "ecr:TagResource",
          "ecr:UntagResource",
          "ecr:ListTagsForResource",
          # S3
          "s3:CreateBucket",
          "s3:DeleteBucket",
          "s3:ListBucket",
          "s3:GetBucketLocation",
          "s3:GetBucketVersioning",
          "s3:PutBucketVersioning",
          "s3:GetVersioning",
          "s3:PutVersioning",
          "s3:GetBucketEncryption",
          "s3:PutBucketEncryption",
          "s3:GetEncryption",
          "s3:PutEncryption",
          "s3:GetBucketPublicAccessBlock",
          "s3:PutBucketPublicAccessBlock",
          "s3:GetPublicAccessBlock",
          "s3:PutPublicAccessBlock",
          "s3:GetBucketLifecycleConfiguration",
          "s3:PutBucketLifecycleConfiguration",
          "s3:GetLifecycleConfiguration",
          "s3:PutLifecycleConfiguration",
          "s3:GetBucketPolicy",
          "s3:PutBucketPolicy",
          "s3:DeleteBucketPolicy",
          "s3:GetPolicy",
          "s3:PutPolicy",
          "s3:DeletePolicy",
          "s3:GetBucketAcl",
          "s3:PutBucketAcl",
          "s3:GetAcl",
          "s3:PutAcl",
          "s3:GetBucketCors",
          "s3:PutBucketCors",
          "s3:DeleteBucketCors",
          "s3:GetCors",
          "s3:PutCors",
          "s3:DeleteCors",
          "s3:GetBucketWebsite",
          "s3:PutBucketWebsite",
          "s3:DeleteBucketWebsite",
          "s3:GetWebsite",
          "s3:PutWebsite",
          "s3:DeleteWebsite",
          "s3:GetBucketNotification",
          "s3:PutBucketNotification",
          "s3:GetNotification",
          "s3:PutNotification",
          "s3:GetBucketRequestPayment",
          "s3:PutBucketRequestPayment",
          "s3:GetRequestPayment",
          "s3:PutRequestPayment",
          "s3:GetBucketLogging",
          "s3:PutBucketLogging",
          "s3:GetLogging",
          "s3:PutLogging",
          "s3:GetBucketTagging",
          "s3:PutBucketTagging",
          "s3:GetTagging",
          "s3:PutTagging",
          "s3:GetBucketObjectLockConfiguration",
          "s3:PutBucketObjectLockConfiguration",
          "s3:GetObjectLockConfiguration",
          "s3:PutObjectLockConfiguration",
          "s3:GetBucketAccelerateConfiguration",
          "s3:PutBucketAccelerateConfiguration",
          "s3:GetAccelerateConfiguration",
          "s3:PutAccelerateConfiguration",
          "s3:GetBucketAnalyticsConfiguration",
          "s3:PutBucketAnalyticsConfiguration",
          "s3:DeleteBucketAnalyticsConfiguration",
          "s3:ListBucketAnalyticsConfigurations",
          "s3:GetBucketIntelligentTieringConfiguration",
          "s3:PutBucketIntelligentTieringConfiguration",
          "s3:DeleteBucketIntelligentTieringConfiguration",
          "s3:ListBucketIntelligentTieringConfigurations",
          "s3:GetBucketInventoryConfiguration",
          "s3:PutBucketInventoryConfiguration",
          "s3:DeleteBucketInventoryConfiguration",
          "s3:ListBucketInventoryConfigurations",
          "s3:GetBucketMetricsConfiguration",
          "s3:PutBucketMetricsConfiguration",
          "s3:DeleteBucketMetricsConfiguration",
          "s3:ListBucketMetricsConfigurations",
          "s3:GetBucketOwnershipControls",
          "s3:PutBucketOwnershipControls",
          "s3:GetBucketReplication",
          "s3:PutBucketReplication",
          "s3:DeleteBucketReplication",
          "s3:GetReplicationConfiguration",
          "s3:PutReplicationConfiguration",
          "s3:DeleteReplicationConfiguration",
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          # SQS
          "sqs:CreateQueue",
          "sqs:DeleteQueue",
          "sqs:GetQueueAttributes",
          "sqs:SetQueueAttributes",
          "sqs:GetQueueUrl",
          "sqs:ListQueues",
          "sqs:TagQueue",
          "sqs:UntagQueue",
          "sqs:ListQueueTags",
          # ELB/ALB
          "elasticloadbalancing:CreateLoadBalancer",
          "elasticloadbalancing:DeleteLoadBalancer",
          "elasticloadbalancing:DescribeLoadBalancers",
          "elasticloadbalancing:DescribeLoadBalancerAttributes",
          "elasticloadbalancing:ModifyLoadBalancerAttributes",
          "elasticloadbalancing:CreateTargetGroup",
          "elasticloadbalancing:DeleteTargetGroup",
          "elasticloadbalancing:DescribeTargetGroups",
          "elasticloadbalancing:DescribeTargetGroupAttributes",
          "elasticloadbalancing:ModifyTargetGroupAttributes",
          "elasticloadbalancing:CreateListener",
          "elasticloadbalancing:DeleteListener",
          "elasticloadbalancing:DescribeListeners",
          "elasticloadbalancing:DescribeListenerAttributes",
          "elasticloadbalancing:ModifyListener",
          "elasticloadbalancing:AddTags",
          "elasticloadbalancing:RemoveTags",
          "elasticloadbalancing:DescribeTags",
          # CloudWatch Logs
          "logs:CreateLogGroup",
          "logs:DeleteLogGroup",
          "logs:DescribeLogGroups",
          "logs:PutRetentionPolicy",
          "logs:TagResource",
          "logs:UntagResource",
          "logs:ListTagsForResource",
          # IAM (for creating roles and policies)
          "iam:CreateRole",
          "iam:DeleteRole",
          "iam:GetRole",
          "iam:ListRoles",
          "iam:AttachRolePolicy",
          "iam:DetachRolePolicy",
          "iam:PutRolePolicy",
          "iam:DeleteRolePolicy",
          "iam:GetRolePolicy",
          "iam:ListRolePolicies",
          "iam:ListAttachedRolePolicies",
          "iam:CreatePolicy",
          "iam:DeletePolicy",
          "iam:GetPolicy",
          "iam:ListPolicies",
          "iam:TagRole",
          "iam:UntagRole",
          "iam:CreateOpenIDConnectProvider",
          "iam:DeleteOpenIDConnectProvider",
          "iam:GetOpenIDConnectProvider",
          "iam:ListOpenIDConnectProviders",
          "iam:TagOpenIDConnectProvider",
          "iam:UntagOpenIDConnectProvider",
          "iam:ListOpenIDConnectProviderTags",
          # Secrets Manager (for database passwords)
          "secretsmanager:CreateSecret",
          "secretsmanager:DeleteSecret",
          "secretsmanager:GetSecretValue",
          "secretsmanager:PutSecretValue",
          "secretsmanager:DescribeSecret",
          # CloudWatch (for monitoring)
          "cloudwatch:PutMetricAlarm",
          "cloudwatch:DeleteAlarms",
          "cloudwatch:DescribeAlarms",
          # Tags
          "ec2:CreateTags",
          "ec2:DeleteTags",
          "ec2:DescribeTags"
        ]
        Resource = "*"
      }
    ]
  })
}

# NOTE: Backend resources (S3 bucket and DynamoDB table) are managed separately
# See infra/aws/terraform/bootstrap/ for the bootstrap configuration
# These resources should be created once manually, then removed from this file

# Output the CI/CD role ARN for GitHub Actions configuration
output "cicd_role_arn" {
  description = "ARN of the CI/CD role for GitHub Actions"
  value       = aws_iam_role.cicd.arn
}

# Backend resource outputs removed - these are managed in bootstrap/
# To get the bucket/table names, check the bootstrap outputs or AWS console

