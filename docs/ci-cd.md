# Configurar CI/CD en GitHub

CI/CD significa automatizar dos tareas:

- **CI** comprueba que el código funciona con lint y tests.
- **CD** crea una imagen Docker y la despliega en AWS.

Esta guía empieza después de completar [Crear AWS con Terraform](aws-setup.md).

## Configuración del repositorio

Antes del primer despliegue, revisa estas opciones en GitHub:

| Dónde | Configuración | Valor recomendado |
|---|---|---|
| **Settings > General** | Default branch | `main` |
| **Settings > Actions > General** | Actions permissions | Permitir las acciones de GitHub; los workflows usan acciones oficiales. |
| **Settings > Actions > General** | Workflow permissions | `Read repository contents`. El workflow declara los permisos AWS que necesita. |
| **Settings > Environments** | Entorno | Crear `production` antes del primer deploy. |
| **Settings > Branches** | Ramas protegidas | Añadir protección a `main` y `dev` después de la primera ejecución de CI. |

No crees Access Keys de AWS en GitHub. El proyecto usa OIDC: GitHub obtiene permisos temporales para cada despliegue.

## Ramas y flujo de trabajo

| Rama | Propósito | Puede desplegar en AWS |
|---|---|---|
| `main` | Versión aprobada para producción. | Sí. Cada merge inicia CD. |
| `dev` | Integra cambios que ya pasaron CI. | No. |
| `feature/*` | Un cambio pequeño, por ejemplo `feature/add-endpoint`. | No. |

```text
feature/mi-cambio -> Pull Request a dev -> Pull Request de dev a main -> aprobacion production -> AWS
```

Para crear `dev` la primera vez:

```bash
git checkout main
git pull origin main
git checkout -b dev
git push -u origin dev
```

Para cada cambio, crea una rama desde `dev`, haz commit y push, y abre un Pull Request hacia `dev`. Cuando esté probado, abre un Pull Request de `dev` hacia `main`. No hagas push directo a `main`.

## Reglas de protección de ramas

Después de ver al menos una ejecución de CI, ve a **Settings > Rules > Rulesets**. Si tu repositorio muestra la interfaz anterior, usa **Settings > Branches**. Crea una regla para `main` y otra para `dev`.

| Regla | `main` | `dev` |
|---|---|---|
| Require a pull request before merging | Sí | Sí |
| Require status checks to pass | `Lint y Tests` | `Lint y Tests` |
| Block force pushes | Sí | Sí |
| Restrict deletions | Sí | Sí |
| Required approvals | 1 en equipo | 1 en equipo |

Si trabajas solo, GitHub puede impedir que apruebes tu propio Pull Request. Mantén obligatorios los checks de CI y usa el entorno `production` como confirmación manual antes del deploy.

## Otras opciones recomendadas

- En **Settings > Security**, activa Dependabot alerts y secret scanning si están disponibles para tu repositorio.
- En **Settings > Actions > General**, deja los permisos del workflow en solo lectura; el archivo `cd.yml` solicita explícitamente `id-token: write` solo durante el despliegue.
- En **Settings > Environments > production**, exige aprobación manual para evitar cambios accidentales en AWS.

## Paso 1: guardar tres valores en GitHub

Terraform imprimió tres valores al terminar. En GitHub, abre tu repositorio y ve a **Settings > Secrets and variables > Actions**.

### Crear el secret

En **Secrets**, crea este valor:

| Nombre | Valor que debes pegar |
|---|---|
| `AWS_ROLE_TO_ASSUME` | Output de Terraform `github_actions_role_arn` |

Un secret se oculta en los logs. Aunque un ARN no es una contraseña, lo guardamos ahí para agrupar toda la configuración de acceso AWS.

### Crear las variables

En **Variables**, crea estos dos valores:

| Nombre | Valor que debes pegar |
|---|---|
| `AWS_REGION` | Output de Terraform `aws_region`, por ejemplo `eu-north-1` |
| `PROJECT_NAME` | Output de Terraform `project_name`, por ejemplo `fastapi-cicd` |

En el workflow, `${{ vars.AWS_REGION }}` significa "lee la variable `AWS_REGION` guardada en GitHub". Después se convierte en `AWS_REGION` para los comandos que se ejecutan durante el workflow.

## Paso 2: pedir aprobación antes de desplegar

En GitHub, ve a **Settings > Environments > New environment** y crea uno llamado exactamente `production`.

Activa **Required reviewers** y añádete. A partir de ahora, cada despliegue se detiene antes de cambiar AWS y debes aprobarlo desde la pestaña **Actions**.

## Paso 3: lanzar el primer despliegue

1. Abre la pestaña **Actions** en GitHub.
2. Selecciona **CD - Build y Deploy a AWS**.
3. Pulsa **Run workflow**, elige la rama `main` y confirma.
4. El job construye la imagen y se detiene esperando la aprobación de `production`.
5. Aprueba el despliegue y espera a que ambos jobs estén en verde.

Después abre la dirección `alb_dns_name` que obtuviste con Terraform y añade `/docs`.

## Qué ocurre en cada despliegue

1. GitHub ejecuta lint y tests.
2. GitHub recibe permisos temporales de AWS mediante OIDC. No usa Access Keys almacenadas en GitHub.
3. Construye una imagen Docker y la guarda en ECR con el SHA del commit, por ejemplo `a1b2c3d`.
4. Tras tu aprobación, registra esa imagen como una nueva revisión en ECS.
5. ECS inicia tareas nuevas. El ALB solo les envía tráfico si `/health/ready` responde correctamente.

Terraform crea la infraestructura inicial. GitHub CD gestiona las revisiones de la imagen para que un `terraform apply` posterior no deshaga un despliegue correcto.

## Si algo falla

- El job no puede asumir el rol AWS: revisa que `github_org` y `github_repo` en `terraform.tfvars` coincidan exactamente con GitHub, y que el secret tenga el ARN correcto.
- El deploy espera: entra en **Actions**, abre el workflow y aprueba el entorno `production`.
- ECS no arranca: consulta [Logs y alarmas](cloudwatch-alarms.md).
