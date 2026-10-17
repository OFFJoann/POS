# ─── Imagen: servidor central de licencias ───────────────────────────────────
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Usuario no-root con UID fijo (1000), igual que el POS.
RUN groupadd -r -g 1000 appuser && useradd -r -u 1000 -g appuser -d /app appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ─── Build del dashboard React ───────────────────────────────────────────────
# Se compila en una etapa aparte y solo se copia `dist/` a la imagen final,
# así el runtime no lleva Node ni node_modules.
FROM node:24-alpine AS panel-build

WORKDIR /panel
COPY panel/package.json panel/package-lock.json ./
RUN npm ci

COPY panel/ ./
RUN npm run build

# ─── Imagen final ────────────────────────────────────────────────────────────
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN groupadd -r -g 1000 appuser && useradd -r -u 1000 -g appuser -d /app appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY --chown=appuser:appuser . .
COPY --from=panel-build --chown=appuser:appuser /panel/dist /app/panel/dist

RUN mkdir -p /app/staticfiles /app/data \
    && chown -R appuser:appuser /app \
    && chmod +x /app/docker/entrypoint.sh

USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60"]