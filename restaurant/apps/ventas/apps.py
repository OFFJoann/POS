from django.apps import AppConfig


class VentasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ventas'
    verbose_name = 'Ventas'

    def ready(self):
        """Importa signals al iniciar la app."""
        import apps.ventas.signals
