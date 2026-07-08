# FastAPI CI/CD en AWS ECS Fargate

API de ejemplo construida con **FastAPI**, dockerizada y desplegada en **AWS ECS Fargate** usando **GitHub Actions** con autenticación **OIDC** (sin claves de acceso estáticas). Incluye health checks, logs en CloudWatch y alarmas básicas.

> Esta guía complementa el video tutorial. Aquí encontrarás los pasos que faltan para que puedas desplegarlo por tu cuenta desde cero.

---

## Tabla de contenidos

1. [Requisitos previos](#requisitos-previos)
2. [Estructura del proyecto](#estructura-del-proyecto)
3. [Ejecutar localmente](#ejecutar-localmente)
4. [Despliegue en AWS paso a paso](#despliegue-en-aws-paso-a-paso)
5. [Configuración de GitHub](#configuración-de-github)
6. [Alarmas de CloudWatch](#alarmas-de-cloudwatch)
7. [Encender / apagar el servicio](#encender--apagar-el-servicio)
8. [Troubleshooting](#troubleshooting)

---

## Requisitos previos

- Cuenta de AWS.
- Cuenta de GitHub y repositorio con este código.
- AWS CLI instalado y configurado localmente:

```bash
aws configure
```

- Docker instalado (para pruebas locales).

---

## Estructura del proyecto

```text
.
├── app/                    # Código de la API FastAPI
│   ├── main.py             # Punto de entrada y health checks
│   └── routers/
│       └── items.py        # Endpoints de ejemplo (sin BD)
├── tests/                  # Tests con pytest
├── .github/workflows/
│   ├── ci.yml              # Lint y tests en Pull Requests
│   └── cd.yml              # Build, push a ECR y deploy a ECS
├── Dockerfile              # Imagen multi-stage
├── task-definition.json    # Definición de tarea de ECS (con placeholders)
├── manage_service.py       # Script para encender/apagar el servicio ECS
├── requirements.txt        # Dependencias de producción
└── requirements-dev.txt    # Dependencias de desarrollo
```

---

## Ejecutar localmente

### 1. Crear entorno virtual e instalar dependencias

```bash
python -m venv .venv
# En Windows:
.venv\Scripts\activate
# En Linux/macOS:
source .venv/bin/activate

pip install -r requirements-dev.txt
```

### 2. Ejecutar tests y linting

```bash
pytest tests/ -v
ruff check ./app ./tests
```

### 3. Levantar la API localmente

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Visita: `http://localhost:8000/docs`

### 4. Construir y probar la imagen Docker

```bash
docker build -t fastapi-cicd-ejemplo:local .
docker run -p 8000:8000 fastapi-cicd-ejemplo:local
```

---

## Despliegue en AWS paso a paso

### Variables que usarás a lo largo de la guía

Reemplaza estos valores por los tuyos propios:

```text
AWS_REGION=eu-north-1
AWS_ACCOUNT_ID=123456789012
ECR_REPOSITORY=fastapi-cicd-ejemplo
ECS_CLUSTER=fastapi-cluster
ECS_SERVICE=fastapi-cicd-task-service
ECS_TASK_DEFINITION=fastapi-cicd-task
CONTAINER_NAME=fastapi-api
```

---

### Paso 1: Crear el repositorio en Amazon ECR

```bash
aws ecr create-repository \
  --repository-name fastapi-cicd-ejemplo \
  --region eu-north-1
```

> Guarda la URI del repositorio. Tiene este formato:
> `123456789012.dkr.ecr.eu-north-1.amazonaws.com/fastapi-cicd-ejemplo`

---

### Paso 2: Crear los roles IAM necesarios

Necesitarás tres roles IAM:

1. **EcsExecutionRole**: permite a ECS descargar imágenes y enviar logs a CloudWatch.
2. **EcsTaskRole**: rol que usan los contenedores (opcional, pero recomendado).
3. **GitHubActionsOIDCRole**: rol que asume GitHub Actions a través de OIDC.

#### 2.1 Trust policy para EcsExecutionRole

Crea el archivo `trust-policy-ecs-execution.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

Crea el rol y adjunta la política gestionada:

```bash
aws iam create-role \
  --role-name EcsExecutionRole \
  --assume-role-policy-document file://trust-policy-ecs-execution.json

aws iam attach-role-policy \
  --role-name EcsExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

#### 2.2 Trust policy para EcsTaskRole

Crea el archivo `trust-policy-ecs-task.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

Crea el rol (sin permisos adicionales por ahora, ya que la app no usa BD ni otros servicios AWS):

```bash
aws iam create-role \
  --role-name EcsTaskRole \
  --assume-role-policy-document file://trust-policy-ecs-task.json
```

#### 2.3 Trust policy para GitHubActionsOIDCRole

Crea el archivo `trust-policy-github-oidc.json`. Reemplaza `123456789012` por tu ID de cuenta y `TU_USUARIO/TU_REPO` por el nombre de tu repositorio en GitHub:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:TU_USUARIO/TU_REPO:*"
        }
      }
    }
  ]
}
```

> Nota: usa `StringLike` en lugar de `StringEquals` para el `sub` si quieres que cualquier rama o entorno pueda asumir el rol. Si quieres restringirlo solo a la rama `main`, puedes poner:
> `repo:TU_USUARIO/TU_REPO:ref:refs/heads/main`

Crea el rol:

```bash
aws iam create-role \
  --role-name GitHubActionsOIDCRole \
  --assume-role-policy-document file://trust-policy-github-oidc.json
```

Adjunta la política mínima necesaria para el pipeline. Crea el archivo `github-actions-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:PutImage"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeTaskDefinition",
        "ecs:RegisterTaskDefinition",
        "ecs:DescribeServices",
        "ecs:UpdateService"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": [
        "arn:aws:iam::123456789012:role/EcsExecutionRole",
        "arn:aws:iam::123456789012:role/EcsTaskRole"
      ]
    }
  ]
}
```

Crea la política y adjúntala al rol:

```bash
aws iam create-policy \
  --policy-name GitHubActionsPolicy \
  --policy-document file://github-actions-policy.json

aws iam attach-role-policy \
  --role-name GitHubActionsOIDCRole \
  --policy-arn arn:aws:iam::123456789012:policy/GitHubActionsPolicy
```

#### 2.4 Crear el proveedor OIDC de GitHub en IAM

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --thumbprint-list 6938fd4e98bab03faadb97b34396831e3780aea1 \
  --client-id-list sts.amazonaws.com
```

> Si el proveedor ya existe, AWS devolverá un error. Puedes ignorarlo y continuar.

---

### Paso 3: Crear el clúster de ECS

```bash
aws ecs create-cluster \
  --cluster-name fastapi-cluster \
  --region eu-north-1
```

---

### Paso 4: Crear el Application Load Balancer (ALB)

Necesitas:

- Una VPC con al menos dos subnets públicas en distintas AZ.
- Un Security Group que permita tráfico HTTP (puerto 80) desde internet.
- Un Target Group apuntando al puerto 8000 de las tareas ECS.
- El ALB escuchando en el puerto 80 y forwardando al Target Group.

Puedes crearlo desde la consola de AWS (más sencillo para un primer despliegue) o con estos comandos:

```bash
# Obtener el ID de la VPC por defecto
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query "Vpcs[0].VpcId" --output text)

# Obtener dos subnets públicas
SUBNETS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[:2].SubnetId" --output text | tr '\t' ',')

# Crear Security Group para el ALB
SG_ID=$(aws ec2 create-security-group \
  --group-name fastapi-alb-sg \
  --description "Security group for FastAPI ALB" \
  --vpc-id $VPC_ID \
  --query "GroupId" --output text)

aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0

# Crear Target Group
TG_ARN=$(aws elbv2 create-target-group \
  --name fastapi-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-path /health/ready \
  --query "TargetGroups[0].TargetGroupArn" --output text)

# Crear ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name fastapi-alb \
  --subnets $(echo $SUBNETS | tr ',' ' ') \
  --security-groups $SG_ID \
  --scheme internet-facing \
  --query "LoadBalancers[0].LoadBalancerArn" --output text)

# Crear listener HTTP
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN
```

> Guarda el `TG_ARN` y el DNS del ALB. Lo necesitarás para crear el servicio de ECS.

---

### Paso 5: Crear el Security Group para las tareas de ECS

```bash
TASK_SG_ID=$(aws ec2 create-security-group \
  --group-name fastapi-task-sg \
  --description "Security group for FastAPI ECS tasks" \
  --vpc-id $VPC_ID \
  --query "GroupId" --output text)

# Permitir tráfico desde el ALB al puerto 8000
aws ec2 authorize-security-group-ingress \
  --group-id $TASK_SG_ID \
  --protocol tcp \
  --port 8000 \
  --source-group $SG_ID
```

---

### Paso 6: Crear el servicio de ECS

Antes de crear el servicio, debes registrar una primera revisión del `task-definition.json`. Edita el archivo y reemplaza los placeholders:

- `<AWS_ACCOUNT_ID>` por tu ID de cuenta.
- `<AWS_REGION>` por tu región (ej: `eu-north-1`).
- `<ECR_REPOSITORY_NAME>` por `fastapi-cicd-ejemplo`.

Luego regístrala:

```bash
aws ecs register-task-definition \
  --cli-input-json file://task-definition.json \
  --region eu-north-1
```

Ahora crea el servicio de ECS:

```bash
aws ecs create-service \
  --cluster fastapi-cluster \
  --service-name fastapi-cicd-task-service \
  --task-definition fastapi-cicd-task \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$(echo $SUBNETS)],securityGroups=[$TASK_SG_ID],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=$TG_ARN,containerName=fastapi-api,containerPort=8000" \
  --region eu-north-1
```

> La primera tarea fallará porque aún no hay imagen en ECR. No te preocupes, el pipeline de CD la subirá y actualizará el servicio.

---

### Paso 7: Crear el grupo de logs de CloudWatch

El `task-definition.json` usa `awslogs-create-group: true`, por lo que el grupo se creará automáticamente. Si prefieres crearlo manualmente:

```bash
aws logs create-log-group --log-group-name /ecs/fastapi-cicd-task --region eu-north-1
```

---

## Configuración de GitHub

Ve a tu repositorio en GitHub: **Settings > Secrets and variables > Actions**.

### Secrets (valores sensibles)

| Nombre del secret | Valor |
| --- | --- |
| `AWS_ROLE_TO_ASSUME` | `arn:aws:iam::123456789012:role/GitHubActionsOIDCRole` |

### Variables (no sensibles)

Ve a la pestaña **Variables**.

| Nombre de la variable | Valor |
| --- | --- |
| `AWS_REGION` | `eu-north-1` |
| `ECR_REPOSITORY` | `fastapi-cicd-ejemplo` |
| `ECS_TASK_DEFINITION` | `task-definition.json` |
| `CONTAINER_NAME` | `fastapi-api` |
| `ECS_SERVICE` | `fastapi-cicd-task-service` |
| `ECS_CLUSTER` | `fastapi-cluster` |

### Entorno de aprobación manual

El workflow `cd.yml` usa `environment: production`, lo que significa que el despliegue requiere aprobación manual.

Ve a **Settings > Environments > New environment** y crea un entorno llamado `production`. Opcionalmente, configura **Required reviewers** para que alguien apruebe el deploy antes de que se ejecute.

---

## Alarmas de CloudWatch

Puedes crear alarmas básicas para monitorear el servicio.

### Alarma de CPU alta

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name fastapi-cpu-high \
  --alarm-description "CPU superior al 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ClusterName,Value=fastapi-cluster Name=ServiceName,Value=fastapi-cicd-task-service \
  --evaluation-periods 2 \
  --region eu-north-1
```

### Alarma de memoria alta

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name fastapi-memory-high \
  --alarm-description "Memoria superior al 80%" \
  --metric-name MemoryUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ClusterName,Value=fastapi-cluster Name=ServiceName,Value=fastapi-cicd-task-service \
  --evaluation-periods 2 \
  --region eu-north-1
```

### Alarma por tareas fallidas (health check)

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name fastapi-unhealthy-tasks \
  --alarm-description "Tareas no saludables" \
  --metric-name UnHealthyHostCount \
  --namespace AWS/ApplicationELB \
  --statistic Average \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --dimensions Name=TargetGroup,Value=$TG_ARN Name=LoadBalancer,Value=$ALB_ARN \
  --evaluation-periods 1 \
  --region eu-north-1
```

> Para que estas alarmas te notifiquen, debes crear un SNS Topic y suscribir tu email, luego agregar `--alarm-actions arn:aws:sns:...` a cada comando.

---

## Encender / apagar el servicio

El archivo `manage_service.py` te permite escalar el servicio a 0 o 1 tareas. Úsalo para ahorrar costos cuando no estés usando la API.

Asegúrate de tener configuradas las credenciales de AWS CLI (`aws configure` o variables de entorno).

```bash
# Encender
python manage_service.py start

# Apagar
python manage_service.py stop
```

Puedes sobreescribir el cluster y servicio con variables de entorno:

```bash
$env:AWS_DEFAULT_REGION="eu-north-1"
$env:ECS_CLUSTER_NAME="fastapi-cluster"
$env:ECS_SERVICE_NAME="fastapi-cicd-task-service"
python manage_service.py stop
```

---

## Primer deploy

Una vez configurado todo:

1. Sube los cambios a la rama `main`.
2. Ve a la pestaña **Actions** de tu repositorio.
3. El workflow `CD - Build y Deploy a AWS` se ejecutará automáticamente.
4. El job `build-and-push` construirá la imagen y la subirá a ECR.
5. El job `deploy-to-production` esperará tu aprobación (si configuraste el entorno).
6. Apruébalo y espera a que el deploy termine.
7. Accede a la URL del ALB y prueba los endpoints:

```bash
curl http://<DNS_DEL_ALB>/health/ready
curl http://<DNS_DEL_ALB>/api/v1/items
```

---

## Troubleshooting

### La tarea de ECS no arranca

Revisa los logs en CloudWatch:

```text
CloudWatch > Log groups > /ecs/fastapi-cicd-task
```

Causas comunes:

- No existe la imagen en ECR.
- El health check `/health/ready` no responde.
- El Security Group de las tareas no permite tráfico desde el ALB.
- Las subnets no tienen acceso a internet (si `assignPublicIp=ENABLED`, deben ser subnets públicas).

### GitHub Actions falla al asumir el rol

- Verifica que el proveedor OIDC esté creado en IAM.
- Verifica que el trust policy del rol tenga el nombre correcto de tu repositorio.
- Asegúrate de que el workflow tenga `permissions: id-token: write`.

### Error `Task failed ELB health checks`

- Confirma que la app responde en `/health/ready` dentro del contenedor.
- Verifica que el Target Group use el puerto 8000 y el path `/health/ready`.
- Revisa que el Security Group de las tareas permita tráfico desde el ALB.

### Costos

- Fargate con 1 tarea de 0.25 vCPU y 2 GB tiene un costo aproximado de ~$15-20 USD/mes si está encendido 24/7.
- Apaga el servicio con `manage_service.py stop` cuando no lo uses para reducir costos.
- El ALB tiene un costo fijo mensual aunque no reciba tráfico (~$18 USD/mes). Si solo practicas, considera eliminarlo cuando termines.

---

## Buenas prácticas de seguridad

- No subas credenciales de AWS al repositorio.
- Usa OIDC en lugar de Access Keys estáticas.
- Restringe el trust policy del rol OIDC a tu repositorio y, de ser posible, a la rama `main`.
- Cierra el Security Group del ALB a tu IP si no necesitas que sea público.
- Mantén las dependencias actualizadas.
