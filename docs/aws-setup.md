# Crear infraestructura en AWS con Terraform

Esta guía crea toda la infraestructura necesaria: VPC, ALB, ECR, IAM, ECS cluster, task definition y service.

---

## 1. Preparar credenciales de AWS

Asegúrate de tener AWS CLI configurada:

```bash
aws configure
```

Verifica:

```bash
aws sts get-caller-identity
```

---

## 2. Configurar variables

Copia el archivo de ejemplo:

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
```

Edita `terraform.tfvars`:

```hcl
aws_region   = "eu-north-1"
project_name = "fastapi-cicd"
github_org   = "tu-usuario"
github_repo  = "fastapi-cicd-ejemplo"
```

> Reemplaza `tu-usuario` y `fastapi-cicd-ejemplo` por tus valores reales.

---

## 3. Inicializar Terraform

```bash
cd infra
terraform init
```

Esto descarga los providers de AWS.

---

## 4. Revisar el plan

```bash
terraform plan
```

Terraform muestra todos los recursos que va a crear. Revísalos antes de continuar.

---

## 5. Aplicar la infraestructura

```bash
terraform apply
```

Confirma escribiendo `yes`. Al terminar, Terraform muestra los outputs:

```text
ecr_repository_url        = "123456789012.dkr.ecr.eu-north-1.amazonaws.com/fastapi-cicd-repo"
alb_dns_name              = "fastapi-cicd-alb-123456789.eu-north-1.elb.amazonaws.com"
github_actions_role_arn   = "arn:aws:iam::123456789012:role/fastapi-cicd-github-actions-role"
ecs_cluster_name          = "fastapi-cicd-cluster"
ecs_service_name          = "fastapi-cicd-service"
```

Guarda estos valores, los necesitarás para configurar GitHub.

---

## 6. Configurar GitHub

Sigue [`docs/ci-cd.md`](ci-cd.md) para:

1. Crear el secret `AWS_ROLE_TO_ASSUME` con `github_actions_role_arn`.
2. Crear las variables usando los outputs de Terraform.
3. Crear el entorno `production` con aprobación manual.

---

## 7. Primer deploy

La primera vez que aplicas Terraform, el servicio ECS intentará levantar tareas con la imagen `:latest`, pero aún no existe. Esto es normal.

Para crear la primera imagen, haz push a `main` o ejecuta el workflow manualmente desde la pestaña **Actions**.

---

## 8. Verificar el despliegue

Una vez que el pipeline termine, prueba:

```bash
curl http://<ALB_DNS_NAME>/
curl http://<ALB_DNS_NAME>/health/ready
```

> Reemplaza `<ALB_DNS_NAME>` por el valor de `alb_dns_name`.

---

## 9. Destruir la infraestructura

Cuando termines de practicar y quieras evitar costos:

```bash
cd infra
terraform destroy
```

Esto elimina todos los recursos creados por Terraform.

> El ALB tiene costo fijo mensual aunque no reciba tráfico. Destrúyelo si no lo usas.

---

## Backend remoto (opcional pero recomendado)

Por defecto, Terraform guarda el estado en un archivo local `terraform.tfstate`. Para trabajar en equipo, usa un backend remoto en S3.

Descomenta `infra/backend.tf` y crea previamente:

- Un bucket S3 para el estado.
- Una tabla DynamoDB para el bloqueo (locking).

Luego ejecuta:

```bash
terraform init -reconfigure
```

---

## Troubleshooting

### Error al crear el proveedor OIDC

Si el proveedor OIDC de GitHub ya existe en tu cuenta, Terraform fallará. Puedes importarlo:

```bash
terraform import aws_iam_openid_connect_provider.github arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com
```

### La tarea no arranca

Revisa los logs en CloudWatch:

```text
CloudWatch > Log groups > /ecs/fastapi-cicd
```

Causas comunes:

- No existe la imagen `:latest` en ECR (ejecuta el pipeline primero).
- El health check `/health/ready` no responde.
- El Security Group de las tareas no permite tráfico desde el ALB.

### GitHub Actions falla al asumir el rol

- Verifica que el secret `AWS_ROLE_TO_ASSUME` sea el ARN correcto.
- Asegúrate de que `github_org` y `github_repo` en `terraform.tfvars` coincidan con tu repositorio.
- Confirma que el workflow tenga `permissions: id-token: write`.

### Costos

- Fargate con 1 tarea de 0.25 vCPU y 0.5 GB cuesta ~$10-15 USD/mes si está encendido 24/7.
- El ALB tiene un costo fijo mensual (~$18 USD/mes).
- Destruye todo con `terraform destroy` cuando no practiques.
