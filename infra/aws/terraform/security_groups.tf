# Security Groups
# These resources are only created when use_shared_infra = false

# Security Group for ECS Tasks
resource "aws_security_group" "ecs_tasks" {
  count       = var.use_shared_infra ? 0 : 1
  name        = "${local.infra_name}-ecs-tasks-${var.environment}"
  description = "Security group for ECS tasks"
  vpc_id      = local.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${local.infra_name}-ecs-tasks-sg-${var.environment}"
    }
  )
}

# Security Group for RDS
resource "aws_security_group" "rds" {
  count       = var.use_shared_infra ? 0 : 1
  name        = "${local.infra_name}-rds-${var.environment}"
  description = "Security group for RDS instance"
  vpc_id      = aws_vpc.main[0].id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks[0].id]
    description     = "PostgreSQL access from ECS tasks"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${local.infra_name}-rds-sg-${var.environment}"
    }
  )
}

# Security Group for ALB
resource "aws_security_group" "alb" {
  count       = var.use_shared_infra ? 0 : (var.enable_alb ? 1 : 0)
  name        = "${local.infra_name}-alb-${var.environment}"
  description = "Security group for Application Load Balancer"
  vpc_id      = local.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "HTTP access"
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "HTTPS access"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${local.infra_name}-alb-sg-${var.environment}"
    }
  )
}

# Allow ECS tasks to communicate with ALB
resource "aws_security_group_rule" "ecs_from_alb" {
  count                    = var.use_shared_infra ? 0 : (var.enable_alb ? 1 : 0)
  type                     = "ingress"
  from_port                = 8000
  to_port                  = 8000
  protocol                 = "tcp"
  source_security_group_id = local.alb_security_group_id
  security_group_id        = local.ecs_security_group_id
  description              = "Allow traffic from ALB to ECS tasks"
}
