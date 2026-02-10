# -----------------------------------------------------------------------------
# General Configuration
# -----------------------------------------------------------------------------

variable "company_prefix" {
  description = "Company prefix for resource naming"
  type        = string
  default     = "saasdog"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "import-export"
}

# -----------------------------------------------------------------------------
# Shared Infrastructure References (from shared-infrastructure project)
# -----------------------------------------------------------------------------

variable "shared_vpc_id" {
  description = "VPC ID from shared infrastructure"
  type        = string
}

variable "shared_public_subnet_ids" {
  description = "Public subnet IDs from shared infrastructure"
  type        = list(string)
}

variable "shared_private_subnet_ids" {
  description = "Private subnet IDs from shared infrastructure"
  type        = list(string)
}

variable "shared_ecs_cluster_arn" {
  description = "ECS cluster ARN from shared infrastructure"
  type        = string
}

variable "shared_ecs_cluster_name" {
  description = "ECS cluster name from shared infrastructure"
  type        = string
}

variable "shared_rds_endpoint" {
  description = "RDS endpoint from shared infrastructure (host:port)"
  type        = string
}

variable "shared_rds_address" {
  description = "RDS address (hostname only) from shared infrastructure"
  type        = string
}

variable "shared_rds_security_group_id" {
  description = "RDS security group ID from shared infrastructure"
  type        = string
}

variable "shared_rds_master_password_secret_arn" {
  description = "ARN of secret containing RDS master password"
  type        = string
}

# -----------------------------------------------------------------------------
# Database Configuration
# -----------------------------------------------------------------------------

variable "db_name" {
  description = "Database name for this application"
  type        = string
  default     = "job_runner"
}

variable "db_username" {
  description = "Database username for this application"
  type        = string
  default     = "job_runner"
}

# -----------------------------------------------------------------------------
# ECS Configuration
# -----------------------------------------------------------------------------

variable "ecs_task_cpu" {
  description = "ECS task CPU units"
  type        = number
  default     = 512
}

variable "ecs_task_memory" {
  description = "ECS task memory in MB"
  type        = number
  default     = 1024
}

variable "ecs_desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 1
}

variable "container_port" {
  description = "Container port"
  type        = number
  default     = 8000
}

# -----------------------------------------------------------------------------
# S3 Configuration
# -----------------------------------------------------------------------------

variable "s3_exports_retention_days" {
  description = "Days to retain export files in S3"
  type        = number
  default     = 30
}

# -----------------------------------------------------------------------------
# SQS Configuration
# -----------------------------------------------------------------------------

variable "sqs_visibility_timeout" {
  description = "SQS visibility timeout in seconds"
  type        = number
  default     = 300
}

variable "sqs_max_receive_count" {
  description = "Max receives before moving to DLQ"
  type        = number
  default     = 3
}

# -----------------------------------------------------------------------------
# CloudWatch Configuration
# -----------------------------------------------------------------------------

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

# -----------------------------------------------------------------------------
# CORS Configuration
# -----------------------------------------------------------------------------

variable "allowed_origins" {
  description = "Allowed CORS origins for the application"
  type        = list(string)
  default     = ["http://localhost:3000", "http://localhost:5173"]
}

# -----------------------------------------------------------------------------
# CI/CD Configuration
# -----------------------------------------------------------------------------

variable "github_repository" {
  description = "GitHub repository (format: owner/repo) for OIDC trust policy"
  type        = string
  default     = ""
}

# -----------------------------------------------------------------------------
# Feature Flags
# -----------------------------------------------------------------------------

variable "enable_deletion_protection" {
  description = "Enable deletion protection for critical resources"
  type        = bool
  default     = false
}

variable "enable_ui" {
  description = "Enable UI hosting via S3/CloudFront"
  type        = bool
  default     = true
}
