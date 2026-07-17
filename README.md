# FastAPI CI/CD en AWS ECS Fargate

Laboratorio práctico para aprender cómo una modificación de código llega a producción: FastAPI se empaqueta con Docker, Terraform crea AWS y GitHub Actions prueba y despliega la imagen.

No hace falta conocer CI/CD, Terraform ni AWS antes de empezar. Sigue las guías en este orden y no saltes pasos.

## Qué construirás

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

            AZ1["us-east-2a<br/>Subnet pública 10.0.0.0/24<br/><br/>Contiene:<br/>- ALB Network Interface<br/>- Fargate Task actual"]
            AZ2["us-east-2b<br/>Subnet pública 10.0.1.0/24<br/><br/>Contiene:<br/>- ALB Network Interface<br/>- sin tarea por ahora"]
        end

        subgraph ECS["Amazon ECS Fargate"]
            Cluster[ECS Cluster<br/>fastapi-cicd-cluster]
            Service[ECS Service<br/>fastapi-cicd-service]
            TaskDef[Task Definition<br/>fastapi-cicd-task]
            Task1[Fargate Task<br/>fastapi-cicd-container]
        end

        CW[CloudWatch Logs<br/>/ecs/fastapi-cicd]
        Alarms[CloudWatch Alarms<br/>CPU / Memoria /<br/>UnHealthyHosts]
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
    GitHubRole -->|registra revision y actualiza servicio| Service

    ECR -->|imagen con tag SHA| TaskDef
    Cluster --> Service
    Service --> TaskDef
    TaskDef --> Task1

    Task1 -->|logs| CW
    Cluster -->|métricas| Alarms
    Service -->|métricas| Alarms
    ALB -->|métricas| Alarms

    classDef aws fill:#FF9900,stroke:#232F3E,stroke-width:2px,color:#232F3E;
    classDef github fill:#333333,stroke:#000000,stroke-width:2px,color:#FFFFFF;
    classDef user fill:#1E8900,stroke:#145A00,stroke-width:2px,color:#FFFFFF;

    class ALB,TG,VPC,AZ1,AZ2,IGW,RT,ECR,Cluster,Service,TaskDef,Task1,CW,Alarms aws;
    class Repo,Actions,OIDC,GitHubRole,ExecRole,TaskRole github;
    class User user;
```

### Vista rápida del despliegue

```mermaid
flowchart LR
    Code[Codigo en GitHub] --> CI[CI: lint y tests]
    CI --> CD[CD: build y deploy]
    CD -->|OIDC, sin claves AWS| ECR[ECR: imagen con SHA]
    ECR --> ECS[ECS Fargate]
    Internet --> ALB[ALB HTTP]
    ALB --> ECS
    ECS --> Logs[CloudWatch logs y alarmas]
```

| Concepto | En este proyecto |
|---|---|
| Docker | Empaqueta la API para ejecutarla igual en tu equipo y AWS. |
| Terraform | Archivos que describen y crean la infraestructura AWS. |
| CI | GitHub ejecuta lint y tests antes de integrar cambios. |
| CD | GitHub crea una imagen y actualiza ECS después de aprobar el despliegue. |
| ECS Fargate | Servicio AWS que ejecuta el contenedor sin administrar servidores. |
| OIDC | GitHub obtiene permisos temporales en AWS, sin guardar Access Keys allí. |

## Antes de empezar

Necesitas una cuenta de GitHub, una cuenta AWS con facturación habilitada, Docker, AWS CLI y Terraform 1.10 o superior. Instala:

- [Docker](https://docs.docker.com/get-docker/)
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)
- [Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)

> AWS cobra por los recursos creados. El ALB y Fargate generan coste incluso sin tráfico. Destruye la infraestructura al terminar el laboratorio.

### Free Tier y costes

Una cuenta AWS nueva puede incluir hasta $200 en créditos y un plan gratuito de hasta 6 meses. Este laboratorio puede consumir esos créditos porque usa ALB, Fargate e IPv4 públicas; revisa **AWS Console > Cost and Usage** antes de crear recursos y no cambies al plan de pago si quieres evitar cargos.

Al terminar las pruebas, elimina los recursos con `terraform destroy` desde la carpeta `infra`. Consulta los límites y créditos vigentes en [AWS Free Tier](https://aws.amazon.com/free/).

## Ruta de aprendizaje

1. Crea una copia del repositorio en tu cuenta de GitHub mediante **Fork** y clónala en tu equipo.
2. Comprueba la API localmente con Docker.
3. Prepara el repositorio, las ramas y el entorno `production` con la [Fase 1 de CI/CD](docs/ci-cd.md#fase-1-preparar-github-antes-de-aws).
4. Sigue [Crear infraestructura en AWS](docs/aws-setup.md).
5. Guarda los outputs de Terraform y ejecuta el despliegue con la [Fase 2 de CI/CD](docs/ci-cd.md#fase-2-despues-de-crear-aws).
6. Aprueba el entorno `production` y comprueba la API.
7. Consulta [Logs y alarmas](docs/cloudwatch-alarms.md).

## Probar la API localmente

Inicia Docker Desktop y ejecuta desde la raíz del proyecto:

```bash
docker compose up --build
```

En otra terminal, abre `http://localhost:8000/docs` o ejecuta:

```bash
curl http://localhost:8000/health/ready
```

La respuesta esperada es `{"status":"ready"}`. Detén el contenedor con `docker compose down`.

## Estructura

```text
app/                 API FastAPI
tests/               Tests de la API
infra/               Terraform: red, ECS, ECR, IAM y alarmas
.github/workflows/   Automatizaciones de CI y CD
```

## Límites del laboratorio

El ALB está expuesto por HTTP para simplificar el aprendizaje. Antes de usar esta arquitectura con usuarios reales, añade dominio, certificado ACM, HTTPS, redirección HTTP a HTTPS y una revisión de seguridad/costes.
