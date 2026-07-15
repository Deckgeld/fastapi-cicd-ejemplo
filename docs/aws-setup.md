# Crear AWS con Terraform

Esta guía crea la red, el balanceador, el repositorio de imágenes, ECS, permisos y alarmas. Terraform es una herramienta que compara archivos con tu cuenta AWS y crea lo que falta.

## Antes de ejecutar comandos

1. Crea una copia del repositorio en GitHub. Anota tu usuario y el nombre del repositorio.
2. En AWS, activa MFA en la cuenta root. Para este laboratorio usa un usuario IAM o AWS IAM Identity Center con permisos para crear recursos. No uses la cuenta root para el día a día y nunca copies estas credenciales a GitHub.

Si no tienes credenciales locales, en **AWS Console > IAM > Users** crea un usuario solo para el laboratorio. En **Permissions**, asígnale `AdministratorAccess` temporalmente; en **Security credentials**, crea una Access Key para **Command Line Interface (CLI)**. Reduce sus permisos o elimínalo al terminar el laboratorio.

3. Instala AWS CLI y Terraform. En una terminal Linux, comprueba las instalaciones:

```bash
aws --version
terraform --version
```

4. Configura las credenciales locales. AWS CLI te pedirá Access Key, Secret Key, región y formato de salida. Estas credenciales solo las usa Terraform en tu equipo.

```bash
aws configure
aws sts get-caller-identity
```

El segundo comando debe mostrar tu cuenta AWS. Si falla, corrige las credenciales antes de continuar.

## Paso 1: crear el lugar donde Terraform guarda su estado

Terraform necesita recordar qué recursos creó. Ese registro se llama **state**. Lo guardaremos en un bucket S3 privado para no perderlo si cambias de equipo.

Elige un nombre globalmente único, por ejemplo `tu-usuario-fastapi-state-1234`. En los comandos, reemplaza `<BUCKET_UNICO>` por ese nombre, sin los símbolos `< >`.

```bash
aws s3api create-bucket --bucket <BUCKET_UNICO> --region eu-north-1 --create-bucket-configuration LocationConstraint=eu-north-1
aws s3api put-bucket-versioning --bucket <BUCKET_UNICO> --versioning-configuration Status=Enabled
aws s3api put-public-access-block --bucket <BUCKET_UNICO> --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

Entra en la carpeta `infra` y crea tu configuración local del backend:

```powershell
cd infra
cp backend.hcl.example backend.hcl
```

Abre `backend.hcl`, cambia solo `bucket` por `<BUCKET_UNICO>` y guarda el archivo. No lo subas a Git: ya está ignorado porque identifica recursos de tu cuenta.

## Paso 2: indicar los datos de tu proyecto

Crea tu archivo de variables:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Abre `terraform.tfvars` y completa estos valores:

```hcl
aws_region   = "eu-north-1"           # Region AWS elegida
project_name = "fastapi-cicd"          # Prefijo de los recursos creados
github_org   = "tu-usuario-github"     # Tu usuario u organizacion GitHub
github_repo  = "nombre-del-repo"       # Nombre exacto del repositorio
alarm_email  = "tu-correo@example.com" # Donde recibiras alertas
```

`project_name` genera nombres como `fastapi-cicd-cluster`. No lo cambies después del primer despliegue salvo que sepas que crearás recursos con otros nombres.

## Paso 3: crear la infraestructura

Todavía dentro de `infra`, ejecuta estos comandos en orden:

```bash
terraform init -backend-config=backend.hcl
terraform plan
terraform apply
```

- `init` descarga lo necesario y conecta Terraform con el bucket S3.
- `plan` muestra lo que AWS va a crear. Revísalo; aún no cambia nada.
- `apply` crea los recursos. Escribe `yes` cuando Terraform lo solicite.

Al terminar, guarda tres outputs: `github_actions_role_arn`, `aws_region` y `project_name`. Los usarás en la siguiente guía.

AWS enviará un correo a `alarm_email`. Confirma la suscripción para recibir alertas.

> La primera tarea ECS fallará al iniciar porque la imagen todavía no existe. Es normal: GitHub creará la primera imagen en el siguiente paso.

## Paso 4: continuar en GitHub

Sigue [Configurar CI/CD en GitHub](ci-cd.md). Cuando el workflow termine, obtén la dirección pública ejecutando:

```bash
terraform output alb_dns_name
```

Abre `http://<direccion-del-alb>/docs` en el navegador. Este laboratorio usa HTTP; no introduzcas datos reales.

## Cuando termines el laboratorio

Para detener los costes principales, vuelve a `infra` y ejecuta:

```bash
terraform destroy
```

Terraform también elimina el repositorio ECR y sus imágenes, porque este proyecto es un laboratorio. El bucket S3 del state se conserva para que no pierdas el historial; elimínalo manualmente cuando ya no lo necesites.

El ALB y Fargate generan costes incluso sin tráfico. Destruye los recursos cuando no practiques.
