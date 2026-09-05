"""
Configuración principal del proyecto El Choli.

Django 5+ - Python 3.13+
"""
import os
from pathlib import Path

# ─── Ruta base del proyecto ─────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ─── Seguridad ──────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-cambiame-en-produccion-!@#$%^&*()'
)
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')
ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',') if h.strip()
]
CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        'DJANGO_CSRF_TRUSTED_ORIGINS',
        'https://20e3-45-178-14-186.ngrok-free.app,https://*.ngrok-free.app',
    ).split(',')
    if o.strip()
]

# ─── Aplicaciones instaladas ────────────────────────────────────────────────
INSTALLED_APPS = [
    # Django core
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Apps del sistema
    'apps.usuarios',
    'apps.configuracion',
    'apps.productos',
    'apps.inventario',
    'apps.mesas',
    'apps.ventas',
    'apps.caja',
    'apps.reportes',
]

# ─── Middleware ──────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

# ─── Templates ──────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.ventas.context_processors.caja_abierta',
                'apps.configuracion.context_processors.configuracion',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ─── Base de datos ──────────────────────────────────────────────────────────
# En producción se usa PostgreSQL cuando existe la variable DB_HOST
# (se inyecta desde docker-compose / .env). Sin ella, se usa SQLite (desarrollo).
def _db_engine():
    if os.environ.get('DB_HOST'):
        return {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'el_choli'),
            'USER': os.environ.get('DB_USER', 'el_choli'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'db'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': 60,
        }
    return {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {'timeout': 30},
    }

DATABASES = {'default': _db_engine()}

# ─── Validador de contraseñas ───────────────────────────────────────────────
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

# ─── Archivos estáticos ─────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ─── Fixtures ────────────────────────────────────────────────────────────────
FIXTURE_DIRS = [BASE_DIR / 'fixtures']

# ─── Archivos multimedia ────────────────────────────────────────────────────
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ─── Campo primario por defecto ─────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── Autenticación personalizada ────────────────────────────────────────────
AUTHENTICATION_BACKENDS = [
    'apps.usuarios.backends.CedulaBackend',
]

LOGIN_URL = '/acceder/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/acceder/'

# ─── Configuración de sesión ────────────────────────────────────────────────
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 28800  # 8 horas
SESSION_SAVE_EVERY_REQUEST = True

# ─── Seguridad TLS (detrás de nginx) ───────────────────────────────────────
# Activa cookies seguras y confianza en el proxy de nginx cuando
# DJANGO_ENABLE_SSL=True en el entorno de la aplicación.
_ENABLE_SSL = os.environ.get('DJANGO_ENABLE_SSL', 'False').lower() in ('true', '1', 'yes')
if _ENABLE_SSL:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = False  # el redireccionamiento lo hace nginx
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
