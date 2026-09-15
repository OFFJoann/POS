#!/bin/sh
# ─── Entrypoint del contenedor app de El Choli POS ─────────────────────────
set -e

echo "==> Aplicando migraciones de base de datos..."
python manage.py migrate --noinput

echo "==> Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

# Crear el usuario inicial (por CÉDULA) la primera vez, si está configurado.
# El perfil de vendedor se crea también. La app inicia sesión con el CORREO y
# la contraseña del usuario. El superusuario (is_staff) equivale a
# administrador en los permisos.
if [ -n "$DJANGO_SUPERUSER_CEDULA" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "==> Creando administrador inicial (cédula: $DJANGO_SUPERUSER_CEDULA)..."
    python manage.py shell -c "
import os
from django.contrib.auth.models import User
from apps.usuarios.models import Vendedor

cedula = os.environ['DJANGO_SUPERUSER_CEDULA'].strip()
nombre = os.environ.get('DJANGO_SUPERUSER_NOMBRE', 'Admin')
apellidos = os.environ.get('DJANGO_SUPERUSER_APELLIDOS', 'Administrador')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '').strip()

if Vendedor.objects.filter(cedula=cedula).exists():
    print('El administrador inicial ya existe, se omite.')
else:
    user = User.objects.create_superuser(
        username=cedula,
        password=os.environ['DJANGO_SUPERUSER_PASSWORD'],
        email=email,
        first_name=nombre,
        last_name=apellidos,
    )
    Vendedor.objects.create(
        usuario=user,
        nombre=nombre,
        apellidos=apellidos,
        cedula=cedula,
        email=email or None,
        telefono='3000000000',
        activo=True,
    )
    print(f'Administrador inicial creado (cédula: {cedula}).')
"
fi

echo "==> Iniciando Gunicorn..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout 120 \
    --capture-output