# ============================================================
# STAGE 1: Builder - Instala dependencias con pip
# ============================================================
FROM python:3.12-slim AS builder

WORKDIR /app

# Copiar solo el archivo de dependencias primero (aprovecha el cache de Docker)
COPY requirements.txt .

# Instalar dependencias en un directorio separado para copiarlo limpio
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ============================================================
# STAGE 2: Final - Imagen de producción mínima y segura
# ============================================================
FROM python:3.12-slim AS final

# Crear un usuario no-root por seguridad (buena práctica)
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Copiar solo los binarios instalados del stage anterior (sin pip ni cache)
COPY --from=builder /install /usr/local

# Copiar el código fuente de la aplicación
COPY ./app ./app

# Cambiar al usuario no-root
USER appuser

# Puerto que expone la API
EXPOSE 8000

# Comando de arranque de la API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
