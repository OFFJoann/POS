#!/bin/sh
# ─── Entrypoint del servidor central de licencias ───────────────────────────
set -e

echo "==> Aplicando migraciones..."
python manage.py migrate --noinput

echo "==> Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

# El dashboard React compila con rutas absolutas (/panel/assets/...), así que su
# build se copia dentro de staticfiles para que WhiteNoise lo sirva.
if [ -d /app/panel/dist ]; then
    echo "==> Publicando el dashboard (panel/dist → staticfiles/panel)..."
    rm -rf /app/staticfiles/panel
    mkdir -p /app/staticfiles/panel
    cp -R /app/panel/dist/. /app/staticfiles/panel/
    echo "    Dashboard disponible en /panel/"
else
    echo "==> AVISO: no existe panel/dist; el dashboard quedará vacío."
    echo "    Compílalo con: cd panel && npm ci && npm run build"
fi

# Superusuario para el panel de administración (solo la primera vez).
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "==> Asegurando superusuario ($DJANGO_SUPERUSER_USERNAME)..."
    python manage.py shell -c "
import os
from django.contrib.auth.models import User

username = os.environ['DJANGO_SUPERUSER_USERNAME']
if User.objects.filter(username=username).exists():
    print('El superusuario ya existe, se omite.')
else:
    User.objects.create_superuser(
        username=username,
        email=os.environ.get('DJANGO_SUPERUSER_EMAIL', ''),
        password=os.environ['DJANGO_SUPERUSER_PASSWORD'],
    )
    print(f'Superusuario creado: {username}')
"
fi

echo "==> Iniciando Gunicorn..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-2}" \
    --timeout 60 \
    --capture-output