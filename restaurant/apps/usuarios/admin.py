"""
Configuración del panel de administración para usuarios.
"""
from django.contrib import admin
from .models import Vendedor


@admin.register(Vendedor)
class VendedorAdmin(admin.ModelAdmin):
    """Administración de vendedores."""
    list_display = ['nombre', 'apellidos', 'cedula', 'telefono', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre', 'apellidos', 'cedula', 'telefono']
    list_editable = ['activo']
    ordering = ['nombre']
