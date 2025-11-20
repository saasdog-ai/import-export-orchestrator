# Application Load Balancer Resources

# ALB
resource "aws_lb" "main" {
  count              = var.enable_alb ? 1 : 0
  name               = "${var.project_name}-alb-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb[0].id]
  subnets            = aws_subnet.public[*].id

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
  count    = var.enable_alb ? 1 : 0
  name     = "${var.project_name}-tg-${var.environment}"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id
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

# ALB Listener (HTTP)
resource "aws_lb_listener" "main" {
  count             = var.enable_alb ? 1 : 0
  load_balancer_arn = aws_lb.main[0].arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main[0].arn
  }

  tags = var.common_tags
}

# Output ALB DNS name
output "alb_dns_name" {
  description = "DNS name of the ALB"
  value       = var.enable_alb ? aws_lb.main[0].dns_name : null
}

