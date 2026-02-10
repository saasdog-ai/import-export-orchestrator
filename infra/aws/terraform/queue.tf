# -----------------------------------------------------------------------------
# SQS Queue for Job Processing
# -----------------------------------------------------------------------------

resource "aws_sqs_queue" "job_runner" {
  name = "${local.name_prefix}-job-queue-${var.environment}"

  # Visibility timeout should be longer than the longest job execution time
  visibility_timeout_seconds = var.sqs_visibility_timeout

  # Message retention period (14 days)
  message_retention_seconds = 1209600

  # Long polling wait time (20 seconds)
  receive_wait_time_seconds = 20

  # Dead letter queue configuration
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.job_runner_dlq.arn
    maxReceiveCount     = var.sqs_max_receive_count
  })

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-job-queue-${var.environment}"
  })
}

# Dead Letter Queue for failed messages
resource "aws_sqs_queue" "job_runner_dlq" {
  name = "${local.name_prefix}-job-queue-dlq-${var.environment}"

  message_retention_seconds = 1209600

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-job-queue-dlq-${var.environment}"
  })
}
