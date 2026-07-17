output "ecr_repository_url" {
  description = "URL del repositorio ECR"
  value       = aws_ecr_repository.app.repository_url
}

output "project_name" {
  description = "Prefijo usado para nombrar los recursos; úsalo como PROJECT_NAME en GitHub"
  value       = var.project_name
}

output "aws_region" {
  description = "Región del despliegue; úsala como AWS_REGION en GitHub"
  value       = var.aws_region
}

output "alb_dns_name" {
  description = "DNS del Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "github_actions_role_arn" {
  description = "ARN del rol IAM para GitHub Actions"
  value       = aws_iam_role.github_actions.arn
}

output "ecs_cluster_name" {
  description = "Nombre del cluster de ECS"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "Nombre del servicio de ECS"
  value       = aws_ecs_service.app.name
}
