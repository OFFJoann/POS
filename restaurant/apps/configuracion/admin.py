"""
Configuración del panel de administración para configuracion.
"""
from django.contrib import admin
from .models import Configuracion


@admin.register(Configuracion)
class ConfiguracionAdmin(admin.ModelAdmin):
    """Edición de la configuración general (modelo singleton)."""
    fields = ['nombre_empresa', 'logo', 'qr_consignacion', 'nit', 'direccion', 'telefono']

    def has_add_permission(self, request):
        """Evita crear más de un registro de configuración."""
        return not Configuracion.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """La configuración no se puede eliminar."""
        return False
