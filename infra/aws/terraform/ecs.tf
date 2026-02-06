# ECS Resources

# ECS Cluster - only created when use_shared_infra = false
resource "aws_ecs_cluster" "main" {
  count = var.use_shared_infra ? 0 : 1
  name  = "${local.infra_name}-cluster-${var.environment}"

  # Container Insights disabled to stay within CloudWatch free tier (10 metrics)
  # Enable for production monitoring
  setting {
    name  = "containerInsights"
    value = "disabled"
  }

  tags = var.common_tags
}

# CloudWatch Log Group - always created (project-specific)
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.project_name}-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = var.common_tags
}

# ECS Task Execution Role (for pulling images, writing logs, etc.)
resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.project_name}-ecs-task-execution-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Allow task execution role to read secrets at container start
resource "aws_iam_role_policy" "ecs_task_execution_secrets" {
  name = "${var.project_name}-ecs-exec-secrets-${var.environment}"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          local.db_credentials_secret_arn
        ]
      }
    ]
  })
}

# ECS Task Role (for application-level permissions)
resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-ecs-task-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = var.common_tags
}

# Note: S3 and SQS policies are now defined in iam_app.tf for better organization

# ECS Task Definition - always created (project-specific)
resource "aws_ecs_task_definition" "main" {
  family                   = "${var.project_name}-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.ecs_task_cpu
  memory                   = var.ecs_task_memory

  execution_role_arn = aws_iam_role.ecs_task_execution.arn
  task_role_arn      = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "${var.project_name}-app"
      image = var.container_image != "" ? var.container_image : "${var.project_name}:latest"

      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = local.db_credentials_secret_arn
        }
      ]

      environment = [
        {
          name  = "APP_ENV"
          value = var.environment
        },
        {
          name  = "SCHEDULER_ENABLED"
          value = "true"
        },
        {
          name  = "LOG_LEVEL"
          value = "INFO"
        },
        {
          name  = "CLOUD_PROVIDER"
          value = "aws"
        },
        {
          name  = "CLOUD_STORAGE_BUCKET"
          value = aws_s3_bucket.exports.id
        },
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "AWS_SQS_QUEUE_URL"
          value = aws_sqs_queue.job_runner.url
        },
        {
          name  = "MESSAGE_QUEUE_NAME"
          value = aws_sqs_queue.job_runner.name
        },
        {
          name  = "ALLOWED_ORIGINS"
          value = jsonencode(concat(["http://${aws_s3_bucket_website_configuration.ui.website_endpoint}"], var.allowed_origins))
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "python -c \"import httpx; httpx.get('http://localhost:8000/health', timeout=5)\""]
        interval    = 30
        timeout     = 10
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = var.common_tags
}

# ECS Service - always created (project-specific), uses shared or standalone cluster
resource "aws_ecs_service" "main" {
  name            = "${var.project_name}-service-${var.environment}"
  cluster         = local.ecs_cluster_arn
  task_definition = aws_ecs_task_definition.main.arn
  desired_count   = var.ecs_desired_count
  launch_type     = "FARGATE"

  # Enable ECS Exec for secure container access (e.g., database queries)
  enable_execute_command = true

  network_configuration {
    subnets          = local.private_subnet_ids
    security_groups  = [local.ecs_security_group_id]
    assign_public_ip = false
  }

  # Only add load balancer if ALB is enabled
  dynamic "load_balancer" {
    for_each = var.enable_alb ? [1] : []
    content {
      target_group_arn = aws_lb_target_group.main[0].arn
      container_name   = "${var.project_name}-app"
      container_port   = 8000
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.ecs_task_execution
  ]

  # Conditionally depend on ALB listener if ALB is enabled
  # Note: We can't use conditional in depends_on, so we'll use a dynamic block approach
  # The load_balancer block above already handles the conditional

  tags = var.common_tags
}
