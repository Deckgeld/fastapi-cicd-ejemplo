# Alarmas de CloudWatch

Las alarmas principales se crean automáticamente con Terraform (`infra/cloudwatch.tf`).

Si prefieres crearlas manualmente, también puedes usar los comandos de AWS CLI más abajo.

---

## Alarmas gestionadas por Terraform

| Alarma | Métrica | Descripción |
|---|---|---|
| `fastapi-cicd-cpu-high` | CPUUtilization | CPU superior al 80% |
| `fastapi-cicd-memory-high` | MemoryUtilization | Memoria superior al 80% |
| `fastapi-cicd-unhealthy-hosts` | UnHealthyHostCount | Tareas no saludables en el ALB |

Para recibir notificaciones, añade `alarm_actions` con el ARN de un SNS Topic en `infra/cloudwatch.tf`.

---

## Crear alarmas manualmente con AWS CLI

### Alarma de CPU alta

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name fastapi-cicd-cpu-high \
  --alarm-description "CPU superior al 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ClusterName,Value=fastapi-cicd-cluster Name=ServiceName,Value=fastapi-cicd-service \
  --evaluation-periods 2 \
  --region eu-north-1
```

### Alarma de memoria alta

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name fastapi-cicd-memory-high \
  --alarm-description "Memoria superior al 80%" \
  --metric-name MemoryUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ClusterName,Value=fastapi-cicd-cluster Name=ServiceName,Value=fastapi-cicd-service \
  --evaluation-periods 2 \
  --region eu-north-1
```

### Alarma por tareas no saludables

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name fastapi-cicd-unhealthy-hosts \
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

> Para recibir notificaciones, crea un SNS Topic, suscríbe tu email y agrega `--alarm-actions arn:aws:sns:...` a cada comando.
