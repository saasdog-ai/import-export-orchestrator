# IAM Roles and Policies for Application Runtime (ECS Tasks)

# Enhanced IAM Policy for ECS Task Role - S3 Access
# This policy allows the application to read/write export files
resource "aws_iam_role_policy" "ecs_task_s3_enhanced" {
  name = "${var.project_name}-ecs-task-s3-enhanced-${var.environment}"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketLocation",
          "s3:GetObjectVersion"
        ]
        Resource = [
          aws_s3_bucket.exports.arn,
          "${aws_s3_bucket.exports.arn}/*"
        ]
      }
    ]
  })
}

# Enhanced IAM Policy for ECS Task Role - SQS Access
# This policy allows the application to send/receive messages from SQS
resource "aws_iam_role_policy" "ecs_task_sqs_enhanced" {
  name = "${var.project_name}-ecs-task-sqs-enhanced-${var.environment}"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:GetQueueUrl",
          "sqs:ChangeMessageVisibility"
        ]
        Resource = [
          aws_sqs_queue.job_runner.arn,
          aws_sqs_queue.job_runner_dlq.arn
        ]
      }
    ]
  })
}

# IAM Policy for ECS Task Role - CloudWatch Logs
# This policy allows the application to write logs to CloudWatch
resource "aws_iam_role_policy" "ecs_task_logs" {
  name = "${var.project_name}-ecs-task-logs-${var.environment}"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.ecs.arn}:*"
      }
    ]
  })
}

# IAM Policy for ECS Task Role - Secrets Manager
# Allows the application to read the database password from Secrets Manager
resource "aws_iam_role_policy" "ecs_task_secrets" {
  name = "${var.project_name}-ecs-task-secrets-${var.environment}"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          aws_secretsmanager_secret.db_password.arn
        ]
        Condition = {
          StringEquals = {
            "secretsmanager:ResourceTag/Environment" = var.environment
            "secretsmanager:ResourceTag/Project"     = var.project_name
          }
        }
      }
    ]
  })
}

# IAM Policy for ECS Exec - allows secure shell access to containers
resource "aws_iam_role_policy" "ecs_task_ssm" {
  name = "${var.project_name}-ecs-task-ssm-${var.environment}"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssmmessages:CreateControlChannel",
          "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel",
          "ssmmessages:OpenDataChannel"
        ]
        Resource = "*"
      }
    ]
  })
}

# Output the ECS Task Role ARN for reference
output "ecs_task_role_arn" {
  description = "ARN of the ECS task role (for application runtime permissions)"
  value       = aws_iam_role.ecs_task.arn
}

output "ecs_task_execution_role_arn" {
  description = "ARN of the ECS task execution role (for ECS service operations)"
  value       = aws_iam_role.ecs_task_execution.arn
}

