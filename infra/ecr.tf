resource "aws_ecr_repository" "app" {
  name                 = "${var.project_name}-repo"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  # Es un laboratorio: destroy también elimina las imágenes almacenadas.
  force_delete = true

  tags = {
    Name = "${var.project_name}-repo"
  }
}
