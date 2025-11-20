# AWS Provider Configuration
terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Backend configuration (use S3 + DynamoDB for state locking)
  # Uncomment and configure when setting up remote state
  # backend "s3" {
  #   bucket         = "your-terraform-state-bucket"
  #   key            = "import-export-orchestrator/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "terraform-state-lock"
  # }
}

# Configure AWS Provider
# Authentication via AWS CLI profile, environment variables, or IAM role
# DO NOT store credentials in this file
provider "aws" {
  region = var.aws_region

  # Use default AWS credential chain:
  # 1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
  # 2. AWS credentials file (~/.aws/credentials)
  # 3. IAM instance profile or ECS task role
  # 4. ECS container credentials
}

