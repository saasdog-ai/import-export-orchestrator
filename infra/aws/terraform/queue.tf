# SQS Queue for Job Processing

resource "aws_sqs_queue" "job_runner" {
  name = "${var.project_name}-job-queue-${var.environment}"

  # Visibility timeout should be longer than the longest job execution time
  # Default: 5 minutes (300 seconds)
  visibility_timeout_seconds = var.sqs_visibility_timeout

  # Message retention period (14 days)
  message_retention_seconds = 1209600

  # Long polling wait time (20 seconds)
  receive_wait_time_seconds = var.sqs_receive_wait_time

  # Dead letter queue configuration
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.job_runner_dlq.arn
    maxReceiveCount     = var.sqs_max_receive_count
  })

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-job-queue-${var.environment}"
  })
}

# Dead Letter Queue for failed messages
resource "aws_sqs_queue" "job_runner_dlq" {
  name = "${var.project_name}-job-queue-dlq-${var.environment}"

  message_retention_seconds = 1209600  # 14 days

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-job-queue-dlq-${var.environment}"
  })
}

