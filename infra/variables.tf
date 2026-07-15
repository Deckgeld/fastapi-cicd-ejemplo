# Variables globales del proyecto

variable "aws_region" {
  description = "Región de AWS donde se desplegará la infraestructura"
  type        = string
  default     = "eu-north-1"
}

variable "project_name" {
  description = "Nombre del proyecto, usado para nombrar recursos"
  type        = string
  default     = "fastapi-cicd"
}

variable "container_port" {
  description = "Puerto expuesto por el contenedor"
  type        = number
  default     = 8000
}

variable "github_org" {
  description = "Usuario u organización de GitHub"
  type        = string
}

variable "github_repo" {
  description = "Nombre del repositorio en GitHub"
  type        = string
}

variable "alarm_email" {
  description = "Correo que recibirá las alarmas de CloudWatch; confirma la suscripción que enviará SNS"
  type        = string
}
