# Application Load Balancer Resources
# ALB is always project-specific (not shared), but uses shared VPC/subnets if use_shared_infra = true

# ALB
resource "aws_lb" "main" {
  count = var.enable_alb ? 1 : 0
  # ALB name must be <= 32 characters
  name               = substr("${var.project_name}-alb-${var.environment}", 0, 32)
  internal           = false
  load_balancer_type = "application"
  security_groups    = [local.alb_security_group_id]
  subnets            = local.public_subnet_ids

  enable_deletion_protection = var.environment == "prod"
  enable_http2               = true

  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-alb-${var.environment}"
    }
  )
}

# Target Group
resource "aws_lb_target_group" "main" {
  count = var.enable_alb ? 1 : 0
  # Target group name must be <= 32 characters
  name        = substr("${var.project_name}-tg-${var.environment}", 0, 32)
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = local.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 10
    interval            = 30
    path                = "/health"
    protocol            = "HTTP"
    matcher             = "200"
  }

  deregistration_delay = 30

  tags = var.common_tags
}

# ALB Listener (HTTP) — forwards traffic when no HTTPS certificate is configured
resource "aws_lb_listener" "http" {
  count             = var.enable_alb && var.acm_certificate_arn == "" ? 1 : 0
  load_balancer_arn = aws_lb.main[0].arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main[0].arn
  }

  tags = var.common_tags
}

# ALB Listener (HTTP -> HTTPS redirect) — only when ACM certificate is provided
resource "aws_lb_listener" "http_redirect" {
  count             = var.enable_alb && var.acm_certificate_arn != "" ? 1 : 0
  load_balancer_arn = aws_lb.main[0].arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }

  tags = var.common_tags
}

# ALB Listener (HTTPS) — only when ACM certificate is provided
resource "aws_lb_listener" "https" {
  count             = var.enable_alb && var.acm_certificate_arn != "" ? 1 : 0
  load_balancer_arn = aws_lb.main[0].arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.acm_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main[0].arn
  }

  tags = var.common_tags
}

# Note: ALB DNS name output is defined in outputs.tf to avoid duplication
