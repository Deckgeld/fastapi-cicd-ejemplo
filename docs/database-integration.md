# Integrar PostgreSQL en la siguiente versión

Esta guía describe cómo añadir persistencia de datos al proyecto sin cambiar la versión actual. El objetivo es un laboratorio económico con Amazon RDS for PostgreSQL Single-AZ.

## Decisión de arquitectura

Usa PostgreSQL cuando la API necesite entidades relacionadas, transacciones, filtros o migraciones de esquema. No uses SQLite en ECS: el sistema de archivos de una tarea Fargate es efímero y cada tarea tendría una copia distinta.

La arquitectura objetivo es:

```text
Cliente -> ALB -> ECS/FastAPI -> RDS PostgreSQL privado
                                  ^
                         Secrets Manager
```

RDS no será público. Solo las tareas ECS podrán conectarse al puerto `5432` mediante un security group.

## Coste del laboratorio

Para reducir el coste:

- Usa RDS PostgreSQL Single-AZ y la clase más pequeña disponible y compatible, por ejemplo `db.t3.micro`.
- Activa una retención de backups de un día.
- No actives Multi-AZ ni RDS Proxy en esta versión.
- Destruye RDS al terminar el laboratorio; una instancia detenida sigue generando costes de almacenamiento y backups.

El precio depende de `us-east-2`, la clase elegida, almacenamiento y backups. Revísalo en la calculadora de AWS antes de aplicar Terraform.

## Desarrollo local

Añade PostgreSQL a `docker-compose.yml` con un volumen persistente y un health check. La aplicación local debe recibir una URL como esta:

```text
postgresql+asyncpg://app:contraseña@db:5432/fastapi_cicd
```

Guarda ese valor en `.env`, ignóralo en Git y publica solo un `.env.example` sin contraseñas reales.

Añade estas dependencias a la aplicación:

- `sqlalchemy[asyncio]` para el ORM y sesiones asíncronas.
- `asyncpg` como controlador PostgreSQL asíncrono.
- `alembic` para migraciones.
- `pydantic-settings` para leer configuración del entorno.

No abras una conexión a la BD durante la importación de módulos. Crea el engine y las sesiones mediante dependencias de FastAPI para que los tests unitarios sigan siendo aislados.

## Aplicación y health checks

Organiza el código nuevo de forma simple:

```text
app/config.py       Configuración DATABASE_URL
app/db.py           Engine, sesiones y dependencia get_db
app/models/         Modelos SQLAlchemy
app/schemas/        Esquemas de entrada y salida
app/routers/        Endpoints que usan get_db
migrations/         Revisiones de Alembic
```

Mantén un endpoint `/health/live` que solo confirme que FastAPI está en ejecución. Haz que `/health/ready` ejecute una consulta corta, por ejemplo `SELECT 1`, y responda `503` si PostgreSQL no está disponible. El ALB debe usar `/health/ready` para no enviar tráfico a tareas que no pueden atender peticiones.

## Migraciones con Alembic

No crees tablas desde el inicio de FastAPI. Versiona los cambios de esquema con Alembic:

```bash
alembic revision --autogenerate -m "create users table"
alembic upgrade head
```

Versiona cada revisión en Git. Antes de desplegar, revísala y pruébala contra PostgreSQL local. Diseña migraciones compatibles hacia adelante: primero añade columnas o tablas, luego despliega el código que las usa y elimina campos antiguos en una versión posterior.

## Infraestructura AWS con Terraform

En una futura implementación, añade `infra/database.tf` con estos recursos:

1. Dos subredes privadas en `infra/vpc.tf` y un DB subnet group que las use.
2. Un security group de RDS que acepte TCP `5432` solo desde `aws_security_group.task`.
3. Una instancia `aws_db_instance` PostgreSQL con `publicly_accessible = false`, cifrado habilitado, Single-AZ y backups de un día.
4. Una contraseña administrada por RDS en Secrets Manager. No escribas contraseñas en `terraform.tfvars`, GitHub ni código.
5. Alarmas de CloudWatch para CPU, conexiones y espacio libre de RDS, enviadas al SNS existente.

Las tareas ECS pueden permanecer en las subredes públicas para esta versión económica. La BD seguirá privada porque no tiene IP pública y su security group solo permite el tráfico desde ECS. En una versión de producción, mueve también ECS a subredes privadas y evalúa NAT Gateway o endpoints VPC.

## Secretos y permisos

ECS debe recibir los datos de conexión desde Secrets Manager, no desde variables de GitHub. El execution role de ECS necesita únicamente `secretsmanager:GetSecretValue` sobre el secreto de la aplicación y `kms:Decrypt` si el secreto usa una clave KMS propia.

La aplicación puede recibir `DB_HOST`, `DB_NAME`, `DB_USER` y `DB_PASSWORD` como secretos o variables de entorno y construir `DATABASE_URL` al iniciar. Para producción, usa un usuario de aplicación con permisos mínimos; no uses el usuario administrador de RDS.

## CI y despliegue

Amplía `ci.yml` con un servicio PostgreSQL temporal. Ejecuta las migraciones y las pruebas de integración contra esa base efímera.

Antes de actualizar el servicio ECS, `cd.yml` debe lanzar una tarea Fargate puntual con la misma imagen y el comando:

```bash
alembic upgrade head
```

El workflow espera a que esa tarea termine correctamente. Si la migración falla, no actualiza el servicio. No ejecutes migraciones en el arranque de FastAPI: durante un rolling deploy pueden coexistir dos tareas y competir por el mismo cambio de esquema.

GitHub conserva el mismo modelo de seguridad actual: usa OIDC para asumir el rol de despliegue. La contraseña de PostgreSQL nunca pasa por GitHub.

## Rollback y recuperación

El rollback de ECS devuelve la imagen anterior, pero no deshace automáticamente una migración de base de datos. Para cambios peligrosos:

- Haz backups antes de migraciones importantes.
- Incluye un `downgrade` probado cuando sea viable.
- Prefiere migraciones expand/contract para que la versión anterior y la nueva funcionen durante el despliegue.
- Restaura un snapshot de RDS solo como última opción, porque puede perder datos recientes.

## Checklist de implementación

- [ ] PostgreSQL local y `.env.example` sin secretos.
- [ ] Modelos, repositorios y pruebas de integración.
- [ ] Alembic con primera migración revisada.
- [ ] Subredes privadas, security group y RDS privado en Terraform.
- [ ] Secretos inyectados desde Secrets Manager en ECS.
- [ ] Alarmas, backups y límites de coste configurados.
- [ ] Tarea de migración antes del despliegue ECS.
- [ ] Prueba de rollback de aplicación y restauración de backup.
