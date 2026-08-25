"""
Configuración de la aplicación configuracion.
"""
from django.apps import AppConfig


class ConfiguracionConfig(AppConfig):
    """Configuración de la app de configuración general del sistema."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.configuracion'
    verbose_name = 'Configuración'
