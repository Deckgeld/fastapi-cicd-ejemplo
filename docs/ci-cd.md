# CI/CD con GitHub Actions

Este proyecto usa dos workflows:

| Workflow | Archivo | Disparador | Qué hace |
|---|---|---|---|
| **CI** | `.github/workflows/ci.yml` | Pull Request a `dev` o `main` | Tests y linting |
| **CD** | `.github/workflows/cd.yml` | Push a `main` | Build, push a ECR y deploy a ECS |

---

## Ramas y flujo de trabajo

Usamos un **Git Flow simplificado**:

```text
feature/*  ──▶  dev  ──▶  main
```

1. Crea una rama desde `dev`:

```bash
git checkout -b feature/mi-cambio
```

2. Trabaja y abre un **Pull Request** hacia `dev`.
3. Si pasa CI, haz merge a `dev`.
4. Cuando esté listo, abre un PR de `dev` a `main`.
5. Al mergear a `main`, se ejecuta CD y despliega en AWS.

---

## Reglas de protección de ramas

Ve a:

```
Settings > Branches > Add branch ruleset
```

Configura para `main` y `dev`:

| Regla | Recomendación |
|---|---|
| **Restrict deletions** | Activar |
| **Require pull request before merging** | Activar |
| **Required approvals** | 1 |
| **Dismiss stale approvals** | Activar |
| **Require status checks to pass** | Activar |
| **Status check** | `Lint y Tests` |
| **Block force pushes** | Activar |

---

## Conexión GitHub ↔ AWS (OIDC)

GitHub Actions no usa Access Keys. En su lugar:

1. GitHub genera un token OIDC firmado.
2. AWS verifica ese token contra el proveedor OIDC configurado en `infra/iam.tf`.
3. Si el token es válido y viene del repositorio correcto, AWS permite asumir el rol `fastapi-cicd-github-actions-role`.
4. GitHub Actions usa ese rol temporal para subir imágenes a ECR y actualizar ECS.

---

## Configuración de GitHub

### Secrets

Ve a:

```
Settings > Secrets and variables > Actions > New repository secret
```

| Nombre | Valor | De dónde sale |
|---|---|---|
| `AWS_ROLE_TO_ASSUME` | `arn:aws:iam::123456789012:role/fastapi-cicd-github-actions-role` | Output de Terraform `github_actions_role_arn` |

> Reemplaza `123456789012` por tu ID de cuenta de AWS.

### Variables

Ve a:

```
Settings > Secrets and variables > Actions > Variables > New repository variable
```

| Nombre | Valor | Descripción |
|---|---|---|
| `AWS_REGION` | `eu-north-1` | Región de AWS |
| `ECR_REPOSITORY` | `fastapi-cicd-repo` | Nombre del repositorio ECR |
| `ECS_TASK_DEFINITION` | `fastapi-cicd-task` | Familia de la task definition |
| `CONTAINER_NAME` | `fastapi-cicd-container` | Nombre del contenedor en la task |
| `ECS_SERVICE` | `fastapi-cicd-service` | Nombre del servicio ECS |
| `ECS_CLUSTER` | `fastapi-cicd-cluster` | Nombre del cluster ECS |

---

## Entorno de aprobación manual

El workflow de CD usa:

```yaml
environment: production
```

Esto pausa el deploy hasta que alguien lo apruebe.

Configúralo en:

```
Settings > Environments > New environment
```

- Nombre: `production`
- **Required reviewers**: activa y agrega tu usuario.

---

## Qué pasa cuando haces push a main

```text
1. CI ya pasó en el Pull Request
        │
        ▼
2. CD inicia el job build-and-push
        │
        ▼
3. GitHub Actions se autentica en AWS con OIDC
        │
        ▼
4. Hace login en ECR
        │
        ▼
5. Construye imagen Docker
   docker build -t cuenta.dkr.ecr.region.amazonaws.com/fastapi-cicd-repo:abc123 .
        │
        ▼
6. Sube imagen con dos tags:
   - abc123 (SHA del commit)
   - latest
        │
        ▼
7. Inicia deploy-to-production
   (espera aprobación manual si configuraste el entorno)
        │
        ▼
8. Descarga la task definition actual desde ECS
        │
        ▼
9. Reemplaza la imagen por la nueva
        │
        ▼
10. Registra una nueva revisión de la task definition
        │
        ▼
11. Actualiza el servicio ECS para usar la nueva revisión
        │
        ▼
12. ECS realiza Rolling Update:
    - Levanta nuevas tareas con la nueva imagen
    - El ALB marca como healthy las que pasan /health/ready
    - Detiene las tareas viejas
        │
        ▼
13. La app actualizada está disponible en el DNS del ALB
```

---

## Cómo ver el estado

- Ve a la pestaña **Actions** de tu repositorio.
- Revisa logs de cada job si algo falla.
- En AWS, revisa **CloudWatch > Log groups > /ecs/fastapi-cicd**.
