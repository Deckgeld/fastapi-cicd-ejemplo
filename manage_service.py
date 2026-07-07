import sys
import os
import boto3
from dotenv import load_dotenv

# Cargar las variables de entorno desde el archivo .env
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Obtener credenciales de AWS desde el entorno local
aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
region = os.getenv('AWS_DEFAULT_REGION', 'eu-north-1')

# Inicializar el cliente de ECS
ecs = boto3.client(
    'ecs',
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key,
    region_name=region
)

# Configuración de los recursos de AWS del proyecto
CLUSTER_NAME = 'fastapi-cluster'
SERVICE_NAME = 'fastapi-cicd-task-service-wcbes888'

def scale_service(desired_count: int):
    """Actualiza el número de tareas deseadas del servicio de ECS."""
    try:
        action_name = "ENCENDIENDO (1 tarea)" if desired_count > 0 else "APAGANDO (0 tareas)"
        print(f"Iniciando acción: {action_name}...")
        print(f"Clúster: {CLUSTER_NAME} | Servicio: {SERVICE_NAME}")
        
        # Llamar a la API de ECS para actualizar el servicio
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
        print("Verifica que las credenciales en tu archivo .env sean válidas y tengan permisos sobre ECS.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Falta especificar la acción.")
        print("Uso:")
        print("  Para encender el servicio:  python manage_service.py start")
        print("  Para apagar el servicio:    python manage_service.py stop")
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
