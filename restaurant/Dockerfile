# ─── Imagen base: Python 3.13 slim ───────────────────────────────────────────
FROM python:3.13-slim

# ─── Variables de entorno ─────────────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ─── Dependencias del sistema ─────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ─── Usuario no-root con UID fijo (1000) para dar permisos desde el host ──────
RUN groupadd -r -g 1000 appuser && useradd -r -u 1000 -g appuser -d /app appuser

# ─── Directorio de trabajo ────────────────────────────────────────────────────
WORKDIR /app

# ─── Instalar dependencias Python ─────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ─── Copiar código de la aplicación ───────────────────────────────────────────
COPY --chown=appuser:appuser . .

# ─── Directorios para static/media + script de entrada ────────────────────────
RUN mkdir -p /app/staticfiles /app/media \
    && chown -R appuser:appuser /app \
    && chmod +x /app/docker/entrypoint.sh

# ─── Cambiar a usuario no-root ────────────────────────────────────────────────
USER appuser

# ─── Exponer puerto ───────────────────────────────────────────────────────────
EXPOSE 8000

# ─── Entrada (migraciones + estáticos + gunicorn) ─────────────────────────────
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]