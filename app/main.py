from fastapi import FastAPI

app = FastAPI(
    title="API Ejemplo CI/CD",
    description="API mínima para demostrar CI/CD con GitHub Actions, Terraform y AWS ECS Fargate",
    version="1.0.0"
)


@app.get("/", tags=["Root"])
def read_root():
    """Endpoint raíz de la aplicación."""
    return {"message": "Hello from FastAPI CI/CD"}


# --- Health Checks (requeridos por ECS Fargate y el ALB) ---

@app.get("/health/live", tags=["Health"])
def liveness_check():
    """Verifica que el contenedor esté vivo."""
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
def readiness_check():
    """Verifica que la app esté lista para recibir tráfico."""
    return {"status": "ready"}
