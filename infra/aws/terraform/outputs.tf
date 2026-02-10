# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

# ALB
output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.app.dns_name
}

output "alb_url" {
  description = "URL to access the application"
  value       = "http://${aws_lb.app.dns_name}"
}

# ECS
output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = local.ecs_cluster_name
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.app.name
}

output "task_definition_arn" {
  description = "ARN of the ECS task definition"
  value       = aws_ecs_task_definition.app.arn
}

# ECR
output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.app.repository_url
}

# S3
output "s3_bucket_name" {
  description = "Name of the S3 bucket for export files"
  value       = aws_s3_bucket.exports.id
}

# SQS
output "sqs_queue_url" {
  description = "URL of the SQS queue for job processing"
  value       = aws_sqs_queue.job_runner.url
}

output "sqs_queue_name" {
  description = "Name of the SQS queue for job processing"
  value       = aws_sqs_queue.job_runner.name
}

output "sqs_dlq_url" {
  description = "URL of the SQS dead letter queue"
  value       = aws_sqs_queue.job_runner_dlq.url
}
