# Variable definitions for Terraform configuration
# NO secrets or credentials should be defined here

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "import-export-orchestrator"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "database_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "database_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "database_name" {
  description = "Name of the database to create"
  type        = string
  default     = "job_runner"
}

variable "database_username" {
  description = "RDS master username (will be set via environment variable or Secrets Manager)"
  type        = string
  default     = "postgres"
  sensitive   = true
}

variable "database_password" {
  description = "RDS master password (MUST be provided via environment variable or Secrets Manager, never in tfvars)"
  type        = string
  sensitive   = true
  # NO default value - must be provided via environment variable or Secrets Manager
}

variable "ecs_task_cpu" {
  description = "CPU units for ECS task (1024 = 1 vCPU)"
  type        = number
  default     = 512
}

variable "ecs_task_memory" {
  description = "Memory for ECS task in MB"
  type        = number
  default     = 1024
}

variable "ecs_desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 1
}

variable "container_image" {
  description = "Container image URI (e.g., ECR image)"
  type        = string
  default     = ""
}

variable "enable_alb" {
  description = "Enable Application Load Balancer"
  type        = bool
  default     = true
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the ALB"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# S3 Configuration
variable "s3_bucket_name" {
  description = "Name for the S3 bucket (will be prefixed with project name and environment)"
  type        = string
  default     = "exports"
}

# SQS Configuration
variable "sqs_visibility_timeout" {
  description = "SQS visibility timeout in seconds (should be longer than longest job execution time)"
  type        = number
  default     = 300 # 5 minutes
}

variable "sqs_receive_wait_time" {
  description = "SQS long polling wait time in seconds"
  type        = number
  default     = 20
}

variable "sqs_max_receive_count" {
  description = "Maximum number of times a message can be received before moving to DLQ"
  type        = number
  default     = 3
}

# CloudWatch Configuration
variable "log_retention_days" {
  description = "CloudWatch log retention in days (1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653)"
  type        = number
  default     = 1
}

# RDS Backup Configuration
variable "rds_backup_retention_period" {
  description = "Number of days to retain automated backups (0 to disable, max 35)"
  type        = number
  default     = 7
}

variable "rds_backup_window" {
  description = "Preferred backup window (UTC). Format: hh24:mi-hh24:mi"
  type        = string
  default     = "03:00-04:00"
}

variable "rds_maintenance_window" {
  description = "Preferred maintenance window (UTC). Format: ddd:hh24:mi-ddd:hh24:mi"
  type        = string
  default     = "mon:04:00-mon:05:00"
}

variable "postgres_version" {
  description = "PostgreSQL engine version for RDS"
  type        = string
  default     = "15"
}

# SQS Message Retention
variable "sqs_message_retention" {
  description = "SQS message retention period in seconds (60 to 1209600)"
  type        = number
  default     = 1209600 # 14 days
}

# CORS / ALB
variable "allowed_origins" {
  description = "Allowed CORS origins for the application"
  type        = list(string)
  default     = ["http://localhost:3000", "http://localhost:4000", "http://localhost:5173"]
}

# HTTPS / TLS
variable "acm_certificate_arn" {
  description = "ACM certificate ARN for HTTPS. Leave empty to use HTTP only."
  type        = string
  default     = ""
}

# GitHub Configuration (for OIDC)
variable "github_repository" {
  description = "GitHub repository in format 'owner/repo' (e.g., 'saasdog-ai/import-export-orchestrator')"
  type        = string
  default     = ""
}

# Tags
variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "import-export-orchestrator"
    ManagedBy   = "terraform"
    Environment = "dev"
  }
}

