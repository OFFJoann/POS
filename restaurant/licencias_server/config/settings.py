"""
Configuración del servidor central de licencias.

Proyecto Django independiente, guardado en licencias_server/.
Usa SQLite por defecto (pocas licencias) y PostgreSQL si DB_HOST
está definido en el entorno (misma convención que el POS).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _cargar_env():
    """Carga las variables del archivo .env (si existe) sin dependencias."""
    ruta = BASE_DIR / '.env'
    if not ruta.exists():
        return
    with open(ruta, encoding='utf-8') as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith('#') or '=' not in linea:
                continue
            clave, _, valor = linea.partition('=')
            clave = clave.strip()
            valor = valor.strip().strip('"').strip("'")
            if clave:
                os.environ.setdefault(clave, valor)


_cargar_env()

# ─── Seguridad ──────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-cambiar-este-secreto-de-licencias'
)
DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() in ('true', '1', 'yes')
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')
    if h.strip()
]

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',')
    if o.strip()
]

# ─── Aplicaciones ────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'licencias',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ─── Base de datos ──────────────────────────────────────────────────────────
def _db_engine():
    if os.environ.get('DB_HOST'):
        return {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'licencias'),
            'USER': os.environ.get('DB_USER', 'licencias'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    return {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get('DB_PATH') or (BASE_DIR / 'db.sqlite3'),
        'OPTIONS': {'timeout': 30},
    }


DATABASES = {'default': _db_engine()}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── Internacionalización ───────────────────────────────────────────────────
LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

# ─── Estáticos ───────────────────────────────────────────────────────────────
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# WhiteNoise sirve los estáticos (incluido el admin) sin necesidad de nginx.
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}
# Build del dashboard React: el entrypoint copia `panel/dist` a
# `staticfiles/panel`, y Vite referencia los assets como `/static/panel/...`
# para que los sirva WhiteNoise igual que los del admin.
PANEL_DIST = BASE_DIR / 'panel' / 'dist'

SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── Secreto de firma de licencias ──────────────────────────────────────────
# Compartido con cada instancia del POS (variable LICENCIA_SECRETO del .env).
# Si queda vacío el token se emite sin firma (el cliente lo rechaza si
# también tiene secreto configurado).
LICENCIA_SECRETO = os.environ.get('LICENCIA_SECRETO', '').strip()

# ─── Seguridad TLS (detrás del router multi-POS) ─────────────────────────────
# Activa cookies seguras y confianza en el proxy cuando el servidor se sirve
# por HTTPS en el router (DJANGO_ENABLE_SSL=True en el .env).
_ENABLE_SSL = os.environ.get('DJANGO_ENABLE_SSL', 'False').lower() in ('true', '1', 'yes')
if _ENABLE_SSL:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = False  # el redireccionamiento lo hace el router
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True