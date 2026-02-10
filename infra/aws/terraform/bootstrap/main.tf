# Bootstrap Terraform Configuration
# This creates the S3 bucket and DynamoDB table for Terraform state
# Run this ONCE manually with local state, then use remote state for main project

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Use local state for bootstrap (chicken-and-egg problem)
  backend "local" {
    path = "bootstrap.tfstate"
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "company_prefix" {
  description = "Company prefix"
  type        = string
  default     = "saasdog"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "import-export"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

locals {
  name_prefix = "${var.company_prefix}-${var.app_name}"
}

# S3 Bucket for Terraform State
resource "aws_s3_bucket" "terraform_state" {
  bucket = "${local.name_prefix}-tfstate-${var.environment}"

  tags = {
    Name        = "${local.name_prefix}-tfstate-${var.environment}"
    Purpose     = "Terraform State Storage"
    ManagedBy   = "terraform"
    Environment = var.environment
    Company     = var.company_prefix
  }
}

# Enable versioning for Terraform state
resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Enable encryption for Terraform state
resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access to Terraform state
resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# DynamoDB Table for Terraform State Locking
resource "aws_dynamodb_table" "terraform_state_lock" {
  name         = "${local.name_prefix}-tflock-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name        = "${local.name_prefix}-tflock-${var.environment}"
    Purpose     = "Terraform State Locking"
    ManagedBy   = "terraform"
    Environment = var.environment
    Company     = var.company_prefix
  }
}

output "terraform_state_bucket" {
  description = "Name of the S3 bucket for Terraform state"
  value       = aws_s3_bucket.terraform_state.id
}

output "terraform_state_lock_table" {
  description = "Name of the DynamoDB table for Terraform state locking"
  value       = aws_dynamodb_table.terraform_state_lock.name
}
