# Logs y alarmas

Terraform crea las alarmas, el topic SNS y la suscripción de correo. No crees estos recursos manualmente: Terraform debe ser la única fuente de cambios de infraestructura.

## Activar notificaciones

Al ejecutar `terraform apply`, AWS envía un correo a la dirección configurada como `alarm_email` en `infra/terraform.tfvars`. Abre el correo y confirma la suscripción. Sin esa confirmación, las alarmas existen pero no entregan avisos.

## Qué vigilan

| Alarma | Significado | Primera acción |
|---|---|---|
| `<proyecto>-cpu-high` | CPU media mayor de 80% durante 10 minutos. | Revisa logs y carga; considera aumentar CPU o número de tareas. |
| `<proyecto>-memory-high` | Memoria media mayor de 80% durante 10 minutos. | Busca fugas o aumenta la memoria de la task. |
| `<proyecto>-unhealthy-hosts` | El ALB detecta una tarea no saludable. | Abre los logs y comprueba `/health/ready`. |

`<proyecto>` es el valor de `project_name`; con la configuración de ejemplo es `fastapi-cicd`.

## Dónde investigar un problema

1. En GitHub, abre **Actions** para comprobar si el despliegue terminó correctamente.
2. En AWS, abre **CloudWatch > Log groups > /ecs/<proyecto>** para ver los logs del contenedor.
3. En AWS, abre **ECS > Clusters > <proyecto>-cluster > Services** para ver eventos, tareas detenidas y el motivo de fallo.
4. En AWS, abre **CloudWatch > Alarms** para consultar el estado y el histórico de cada alarma.

Las alarmas ayudan a detectar problemas; no corrigen ni escalan el servicio automáticamente. Eso sería un siguiente paso del laboratorio.
