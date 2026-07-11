# FastAPI CI/CD en AWS ECS Fargate

Proyecto de aprendizaje de **DevOps**: una API mínima en FastAPI, empaquetada en Docker y desplegada automáticamente en **AWS ECS Fargate** usando **GitHub Actions** y **Terraform**.

> El objetivo no es la API en sí, sino aprender el flujo completo: código → CI → imagen Docker → CD → AWS.

---

## Arquitectura

```mermaid
graph TB
    User([Usuario / Internet]) -->|HTTP 80| IGW

    subgraph GitHub["GitHub"]
        Repo[Repositorio<br/>fastapi-cicd-ejemplo]
        Actions[GitHub Actions<br/>CI / CD]
    end

    Repo -->|Pull Request / Push| Actions

    subgraph IAM["AWS IAM"]
        OIDC[OIDC Provider<br/>token.actions.githubusercontent.com]
        GitHubRole[Rol GitHub Actions<br/>fastapi-cicd-github-actions-role]
        ExecRole[Rol ECS Task Execution<br/>fastapi-cicd-ecs-task-execution-role]
        TaskRole[Rol ECS Task<br/>fastapi-cicd-ecs-task-role]
    end

    Actions -->|token OIDC| OIDC
    OIDC -->|AssumeRoleWithWebIdentity| GitHubRole

    subgraph AWS["AWS Cloud"]
        ECR[Amazon ECR<br/>fastapi-cicd-repo]

        subgraph VPC["VPC 10.0.0.0/16"]
            IGW[Internet Gateway]
            RT[Route Table<br/>0.0.0.0/0 → IGW]
            ALB[Application Load Balancer<br/>fastapi-cicd-alb]
            TG[Target Group<br/>fastapi-cicd-tg:8000]

            AZ1["eu-north-1a<br/>Subnet pública 10.0.0.0/24<br/><br/>Contiene:<br/>- ALB Network Interface<br/>- Fargate Task actual"]
            AZ2["eu-north-1b<br/>Subnet pública 10.0.1.0/24<br/><br/>Contiene:<br/>- ALB Network Interface<br/>- sin tarea por ahora"]
        end

        subgraph ECS["Amazon ECS Fargate"]
            Cluster[ECS Cluster<br/>fastapi-cicd-cluster]
            Service[ECS Service<br/>fastapi-cicd-service]
            TaskDef[Task Definition<br/>fastapi-cicd-task]
            Task1[Fargate Task<br/>fastapi-cicd-container]
        end

        CW[CloudWatch Logs<br/>/ecs/fastapi-cicd]
    end

    IGW -->|tráfico entrante| ALB
    ALB -->|interfaz de red| AZ1
    ALB -->|interfaz de red| AZ2
    ALB -->|distribuye tráfico| TG
    TG -->|health check /health/ready| Task1

    RT --> IGW
    AZ1 -->|ruta por defecto| RT
    AZ2 -->|ruta por defecto| RT
    Task1 -->|se ejecuta en| AZ1

    GitHubRole -->|push imagen| ECR
    GitHubRole -->|register task /<br/>update service| Service

    ECR -->|imagen :latest| TaskDef
    Cluster --> Service
    Service --> TaskDef
    TaskDef --> Task1

    Task1 -->|logs| CW

    classDef aws fill:#FF9900,stroke:#232F3E,stroke-width:2px,color:#232F3E;
    classDef github fill:#333333,stroke:#000000,stroke-width:2px,color:#FFFFFF;
    classDef user fill:#1E8900,stroke:#145A00,stroke-width:2px,color:#FFFFFF;

    class ALB,TG,VPC,AZ1,AZ2,IGW,RT,ECR,Cluster,Service,TaskDef,Task1,CW aws;
    class Repo,Actions,OIDC,GitHubRole,ExecRole,TaskRole github;
    class User user;
```

> **¿Por qué dos zonas de disponibilidad?**
>
> AWS exige al menos **2 subnets en distintas AZ** para crear un ALB. Aunque ahora haya solo 1 tarea en `eu-north-1a`, el ALB también tiene una interfaz de red en `eu-north-1b` para alta disponibilidad.

### Componentes

| Componente | Tecnología | Función |
|---|---|---|
| **Código fuente** | FastAPI + Python | API mínima con health checks |
| **Contenedor** | Docker | Empaqueta la app |
| **CI/CD** | GitHub Actions | Tests, linting, build y deploy |
| **Imágenes** | Amazon ECR | Almacena imágenes Docker |
| **Infraestructura** | Terraform | Crea VPC, ALB, ECS, IAM |
| **Compute** | AWS ECS Fargate | Ejecuta contenedores |
| **Balanceador** | Application Load Balancer | Recibe y reparte tráfico HTTP |
| **Logs** | Amazon CloudWatch | Guarda logs |
| **Auth** | IAM + OIDC | GitHub Actions accede a AWS sin claves estáticas |

### Flujo resumido

```text
feature/* → PR a dev → CI → merge a dev → PR a main → CI → merge a main → CD → AWS ECS
```

Para el flujo completo ver [`docs/ci-cd.md`](docs/ci-cd.md).

---

## Requisitos

- Cuenta de AWS.
- Cuenta de GitHub.
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) configurada (`aws configure`).
- [Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli) >= 1.5.0.
- [Docker](https://docs.docker.com/get-docker/).

---

## Estructura del proyecto

```text
.
├── app/                    # API mínima en FastAPI
├── tests/                  # Tests con pytest
├── infra/                  # Infraestructura con Terraform
├── .github/workflows/      # CI/CD con GitHub Actions
├── docs/                   # Documentación
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── requirements-dev.txt
```

---

## Ejecutar localmente con Docker

La app solo se ejecuta localmente mediante Docker.

### Con Docker Compose

```bash
docker compose up --build
```

### Con Docker directamente

```bash
docker build -t fastapi-cicd-ejemplo:local .
docker run -p 8000:8000 fastapi-cicd-ejemplo:local
```

### Probar la API

```bash
curl http://localhost:8000/
curl http://localhost:8000/health/ready
```

Para detener: `Ctrl+C` o `docker compose down`.

---

## Desplegar en AWS

1. Crea la infraestructura con Terraform: [`docs/aws-setup.md`](docs/aws-setup.md).
2. Configura GitHub: [`docs/ci-cd.md`](docs/ci-cd.md).
3. Haz push a `main` y el pipeline despliega automáticamente.

---

## Documentación

| Archivo | Contenido |
|---|---|
| [`docs/ci-cd.md`](docs/ci-cd.md) | Configuración de GitHub Actions y flujo completo |
| [`docs/aws-setup.md`](docs/aws-setup.md) | Crear infraestructura con Terraform |
| [`docs/cloudwatch-alarms.md`](docs/cloudwatch-alarms.md) | Alarmas básicas de monitoreo |
