from fastapi import FastAPI
from app.routers import items

app = FastAPI(
    title="API Ejemplo CI/CD",
    description="API de ejemplo con FastAPI para demostrar el pipeline CI/CD con AWS ECS Fargate",
    version="1.0.0"
)

# Incluir los routers de negocio
app.include_router(items.router, prefix="/api/v1", tags=["items"])

# --- Health Checks (CRÍTICOS para ECS Fargate) ---

@app.get("/health/live", tags=["Health"])
def liveness_check():
    """
    Liveness Check: Confirma que el proceso está activo y sin deadlock.
    ECS lo usa para saber si debe reiniciar el contenedor.
    """
    return {"status": "alive"}

@app.get("/health/ready", tags=["Health"])
def readiness_check():
    """
    Readiness Check: Confirma que la app está lista para recibir tráfico.
    El ALB solo enviará tráfico cuando este endpoint responda 200.
    """
    return {"status": "ready"}
