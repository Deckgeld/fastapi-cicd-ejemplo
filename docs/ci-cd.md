# Configurar CI/CD en GitHub

CI/CD significa automatizar dos tareas:

- **CI** comprueba que el código funciona con lint y tests.
- **CD** crea una imagen Docker y la despliega en AWS.

Esta guía tiene una fase de preparación de GitHub antes de crear AWS y otra posterior para guardar los outputs de Terraform y desplegar.

## Workflows del proyecto

| Archivo | Cuándo se ejecuta | Qué hace |
|---|---|---|
| `ci.yml` | Pull Request hacia `dev` o `main`, y push a `main` | Instala dependencias, ejecuta lint y tests. El check se llama `Lint y Tests`. |
| `cd.yml` | Push a `main` o ejecución manual | Valida el código, publica la imagen en ECR y, tras aprobar `production`, actualiza ECS. |

El workflow de CD usa OIDC para recibir credenciales AWS temporales. No guarda Access Keys en GitHub.

## Fase 1: preparar GitHub antes de AWS

Antes del primer despliegue, revisa estas opciones en GitHub:

| Dónde | Configuración | Valor recomendado |
|---|---|---|
| **Settings > General** | Default branch | `main` |
| **Settings > Actions > General** | Actions permissions | Permitir las acciones de GitHub; los workflows usan acciones oficiales. |
| **Settings > Actions > General** | Workflow permissions | `Read repository contents`. El workflow declara los permisos AWS que necesita. |
| **Settings > Environments** | Entorno | Crear y configurar `production` antes del primer deploy. Consulta [Crear el entorno `production`](#crear-el-entorno-production). |
| **Settings > Rules > Rulesets** | Ramas protegidas | Crear reglas para `main` y `dev` después de la primera ejecución de CI. Consulta [Reglas de protección de ramas](#reglas-de-proteccion-de-ramas). |

No crees Access Keys de AWS en GitHub. El proyecto usa OIDC: GitHub obtiene permisos temporales para cada despliegue.

## Crear el entorno `production`

En GitHub, ve a **Settings > Environments > New environment** y crea uno llamado exactamente `production`.

| Ajuste | Configuración | Por qué |
|---|---|---|
| **Required reviewers** | Actívalo y añádete. | Obliga a confirmar manualmente cada despliegue. |
| **Deployment branches and tags** | Selecciona solo `main`. | Impide que otra rama despliegue a producción. |

Deja desactivados el temporizador, las reglas de GitHub Apps y el bypass de administradores. Deja vacíos los secretos y variables del entorno: este proyecto no los usa ahí.

El entorno solo protege el job de despliegue con aprobación manual. El job que construye y sube la imagen a ECR se ejecuta antes de entrar en `production`, por lo que sus secretos y variables deben estar a nivel de repositorio.

Pulsa **Save protection rules**. Después continúa con [Crear AWS con Terraform](aws-setup.md).

## Reglas de protección de ramas

Después de ver al menos una ejecución de CI, ve a **Settings > Rules > Rulesets > New branch ruleset**. Crea una regla para `main` y otra para `dev`; usa **Target branches > Add Target > branches Include by pattern** para elegir cada rama. La primera ejecución hace que GitHub muestre el check `Lint y Tests`.

En ambas reglas, activa solo esto:

| Opción | Configuración | Por qué |
|---|---|---|
| **Require a pull request before merging** | Activar | Evita cambios directos en la rama. |
| **Require status checks to pass** | Activar y añadir `Lint y Tests` | Solo permite código que pasa lint y tests. |
| **Block force pushes** | Activar | Evita reescribir el historial compartido. |
| **Restrict deletions** | Activar | Impide borrar la rama por accidente. |

En un equipo, dentro de la opción de Pull Request, exige **1 aprobación**. Si trabajas solo, déjala en `0`: GitHub no permite aprobar tu propio Pull Request. Mantén la regla en estado **Active** y sin personas en **Bypass list**.

Pulsa **Create** y repite la configuración para la otra rama. Si tu repositorio usa la interfaz antigua, la ruta es **Settings > Branches > Add branch protection rule** y las opciones son las mismas.

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

## Otras opciones recomendadas

- En **Settings > Security**, activa Dependabot alerts y secret scanning si están disponibles para tu repositorio.
- En **Settings > Actions > General**, deja los permisos del workflow en solo lectura; el archivo `cd.yml` solicita explícitamente `id-token: write` solo durante el despliegue.
- En **Settings > Environments > production**, exige aprobación manual para evitar cambios accidentales en AWS.

## Fase 2: después de crear AWS

### Guardar tres valores en GitHub

Terraform imprimió tres valores al terminar. En GitHub, abre tu repositorio y ve a **Settings > Secrets and variables > Actions**.

### Crear el secret

En **Secrets**, crea este **Repository secret**:

| Nombre | Valor que debes pegar |
|---|---|
| `AWS_ROLE_TO_ASSUME` | Output de Terraform `github_actions_role_arn` |

Pega el ARN completo del output, no su nombre. No lo crees dentro de `production`: el job de build necesita asumir el rol AWS antes de llegar a ese entorno.

### Crear las variables

En **Variables**, crea estos dos valores:

| Nombre | Valor que debes pegar |
|---|---|
| `AWS_REGION` | Output de Terraform `aws_region`, por ejemplo `us-east-2` |
| `PROJECT_NAME` | Output de Terraform `project_name`, por ejemplo `fastapi-cicd` |

Escribe el valor de cada output, no el nombre de la variable: por ejemplo, el valor de `AWS_REGION` debe ser `us-east-2`, no `AWS_REGION`. Crea estos valores como **Repository variables**, no como variables de `production`.

En el workflow, `${{ vars.AWS_REGION }}` significa "lee la variable `AWS_REGION` guardada en GitHub". Después se convierte en `AWS_REGION` para los comandos que se ejecutan durante el workflow.

El workflow declara `environment: production` en el job **Deploy a Producción**. Por eso, cuando ese job empiece, GitHub lo mostrará como **Waiting**. Abre la ejecución desde **Actions**, pulsa **Review deployments**, selecciona `production`, escribe un comentario opcional y confirma **Approve and deploy**. Solo entonces ese job obtiene credenciales temporales de AWS y actualiza ECS.

## Fase 3: lanzar el primer despliegue

1. Abre la pestaña **Actions** en GitHub.
2. Selecciona **CD - Build y Deploy a AWS**.
3. Pulsa **Run workflow**, elige la rama `main` y confirma.
4. El job construye la imagen y se detiene esperando la aprobación de `production`.
5. Aprueba el despliegue y espera a que ambos jobs estén en verde.

Si no aparece **Run workflow**, abre un Pull Request de `dev` hacia `main` y haz merge. GitHub solo muestra ese botón cuando `cd.yml` con `workflow_dispatch` ya existe en la rama predeterminada (`main`). Ese primer merge inicia el despliegue automáticamente; el botón aparecerá para ejecuciones posteriores.

Después abre la dirección `alb_dns_name` que obtuviste con Terraform y añade `/docs`.

## Qué ocurre en cada despliegue

1. GitHub ejecuta lint y tests.
2. GitHub recibe permisos temporales de AWS mediante OIDC. No usa Access Keys almacenadas en GitHub.
3. Construye una imagen Docker y la guarda en ECR con el SHA del commit, por ejemplo `a1b2c3d`.
4. Tras tu aprobación, registra esa imagen como una nueva revisión en ECS.
5. ECS inicia tareas nuevas. El ALB solo les envía tráfico si `/health/ready` responde correctamente.

Terraform crea la infraestructura inicial. GitHub CD gestiona las revisiones de la imagen para que un `terraform apply` posterior no deshaga un despliegue correcto.

## Volver a una versión anterior

Cada imagen en ECR usa el SHA del commit como etiqueta y ECS conserva las revisiones anteriores de la task definition.

- Si la nueva tarea no inicia o no supera `/health/ready`, ECS usa el deployment circuit breaker y vuelve automáticamente a la última revisión estable.
- Si la aplicación inicia correctamente pero tiene un error funcional, abre **Actions**, selecciona una ejecución anterior que terminó en verde y usa **Re-run all jobs**. Esa ejecución vuelve a publicar y desplegar la imagen del commit anterior.

Después del rollback, crea un Pull Request que revierta o corrija el cambio defectuoso. Así, el código de `main` vuelve a coincidir con la versión que está en producción.

## Si algo falla

- El job no puede asumir el rol AWS: revisa que `github_org` y `github_repo` en `terraform.tfvars` coincidan exactamente con GitHub, y que el secret tenga el ARN correcto.
- El deploy espera: entra en **Actions**, abre el workflow y aprueba el entorno `production`.
- ECS no arranca: consulta [Logs y alarmas](cloudwatch-alarms.md).
