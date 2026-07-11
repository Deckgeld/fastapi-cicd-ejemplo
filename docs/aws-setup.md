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

### ¿Qué es el estado de Terraform?

Terraform guarda un **registro de todo lo que ha creado** en un archivo llamado `terraform.tfstate`. Ese archivo le permite a Terraform saber:

- Qué recursos ya existen en AWS.
- Qué cambiar cuando modificas el código.
- Qué destruir cuando ejecutas `terraform destroy`.

### ¿Por qué usar un backend remoto?

Por defecto, el estado se guarda **localmente** en tu máquina. Esto funciona si trabajas solo, pero tiene problemas:

| Problema | Consecuencia |
|---|---|
| Pierdes el archivo `terraform.tfstate` | Terraform no sabe qué recursos existen. Tendrías que importarlos manualmente uno a uno. |
| Trabajas desde otra máquina | No tienes el estado actualizado y podrías crear recursos duplicados. |
| Trabajas en equipo | Dos personas podrían aplicar cambios simultáneamente y romper la infraestructura. |

Un **backend remoto en S3** resuelve esto:

- El estado se guarda en un bucket de S3 accesible desde cualquier lugar.
- Puedes trabajar desde tu laptop, otra PC o en equipo.
- Puedes añadir una tabla DynamoDB para **bloquear el estado** y evitar que dos personas ejecuten `terraform apply` al mismo tiempo.

### Configurar backend remoto

1. Crea un bucket S3 para el estado:

```bash
aws s3 mb s3://fastapi-cicd-terraform-state --region eu-north-1
aws s3api put-bucket-versioning \
  --bucket fastapi-cicd-terraform-state \
  --versioning-configuration Status=Enabled
```

2. Crea una tabla DynamoDB para el bloqueo:

```bash
aws dynamodb create-table \
  --table-name fastapi-cicd-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region eu-north-1
```

3. Descomenta el contenido de `infra/backend.tf`:

```hcl
terraform {
  backend "s3" {
    bucket         = "fastapi-cicd-terraform-state"
    key            = "terraform.tfstate"
    region         = "eu-north-1"
    encrypt        = true
    dynamodb_table = "fastapi-cicd-terraform-locks"
  }
}
```

4. Reinicializa Terraform:

```bash
cd infra
terraform init -reconfigure
```

Terraform te preguntará si quieres migrar el estado local al backend remoto. Responde **yes**.

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
