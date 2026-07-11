# Alarmas de CloudWatch

Puedes crear alarmas básicas para monitorear el servicio.

## Alarma de CPU alta

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
  --dimensions Name=ClusterName,Value=fastapi-cicd-cluster Name=ServiceName,Value=fastapi-cicd-service \
  --evaluation-periods 2 \
  --region eu-north-1
```

## Alarma de memoria alta

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
  --dimensions Name=ClusterName,Value=fastapi-cicd-cluster Name=ServiceName,Value=fastapi-cicd-service \
  --evaluation-periods 2 \
  --region eu-north-1
```

## Alarma por tareas no saludables

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

> Para recibir notificaciones, crea un SNS Topic, suscríbe tu email y agrega `--alarm-actions arn:aws:sns:...` a cada comando.
