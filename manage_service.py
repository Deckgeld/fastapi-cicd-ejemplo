import sys
import os
import boto3
from dotenv import load_dotenv

# Cargar variables de entorno locales si existen (no obligatorio)
load_dotenv()

# Inicializar el cliente de ECS usando las credenciales configuradas
# en AWS CLI / variables de entorno / perfil por defecto.
# No es necesario pasar access keys explícitas.
region = os.getenv('AWS_DEFAULT_REGION', 'eu-north-1')
ecs = boto3.client('ecs', region_name=region)

# Configuración de los recursos de AWS del proyecto.
# Puedes sobreescribir estos valores con variables de entorno.
CLUSTER_NAME = os.getenv('ECS_CLUSTER_NAME', 'fastapi-cluster')
SERVICE_NAME = os.getenv('ECS_SERVICE_NAME', 'fastapi-cicd-task-service')


def scale_service(desired_count: int):
    """Actualiza el número de tareas deseadas del servicio de ECS."""
    try:
        action_name = "ENCENDIENDO (1 tarea)" if desired_count > 0 else "APAGANDO (0 tareas)"
        print(f"Iniciando acción: {action_name}...")
        print(f"Clúster: {CLUSTER_NAME} | Servicio: {SERVICE_NAME}")

        response = ecs.update_service(
            cluster=CLUSTER_NAME,
            service=SERVICE_NAME,
            desiredCount=desired_count
        )

        print("\n✅ ¡Servicio actualizado con éxito en AWS!")
        print(f"Estado del servicio: {response['service']['status']}")
        print(f"Tareas corriendo actualmente: {response['service']['runningCount']}")
        print(f"Tareas deseadas configuradas: {response['service']['desiredCount']}")
        print("\nNota: Si lo has apagado, las tareas tardarán un par de minutos en detenerse por completo.")
        print("Nota: Si lo has encendido, tardará un momento en levantar y ser validado por el balanceador (ALB).")

    except Exception as e:
        print(f"\n❌ Error al comunicarse con AWS ECS: {e}")
        print("Verifica que tus credenciales de AWS CLI sean válidas y tengan permisos sobre ECS.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Falta especificar la acción.")
        print("Uso:")
        print("  Para encender el servicio:  python manage_service.py start")
        print("  Para apagar el servicio:    python manage_service.py stop")
        print("\nVariables de entorno opcionales:")
        print("  AWS_DEFAULT_REGION   (default: eu-north-1)")
        print("  ECS_CLUSTER_NAME     (default: fastapi-cluster)")
        print("  ECS_SERVICE_NAME     (default: fastapi-cicd-task-service)")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "start":
        scale_service(1)
    elif command == "stop":
        scale_service(0)
    else:
        print(f"Error: Comando '{sys.argv[1]}' no válido.")
        print("Usa únicamente 'start' (para encender) o 'stop' (para apagar).")
        sys.exit(1)
