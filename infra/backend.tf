# Backend remoto para el estado de Terraform.
# Descomenta esta sección después de crear el bucket S3 y la tabla DynamoDB.
#
# terraform {
#   backend "s3" {
#     bucket         = "fastapi-cicd-terraform-state"
#     key            = "terraform.tfstate"
#     region         = "eu-north-1"
#     encrypt        = true
#     dynamodb_table = "fastapi-cicd-terraform-locks"
#   }
# }
