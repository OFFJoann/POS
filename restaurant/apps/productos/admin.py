"""
Configuración del panel de administración para productos.
"""
from django.contrib import admin
from .models import Categoria, UnidadMedida, Producto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    """Administración de categorías."""
    list_display = ['nombre', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre']


@admin.register(UnidadMedida)
class UnidadMedidaAdmin(admin.ModelAdmin):
    """Administración de unidades de medida."""
    list_display = ['nombre', 'abreviatura']
    search_fields = ['nombre']


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    """Administración de productos."""
    list_display = [
        'codigo', 'nombre', 'categoria', 'precio_venta',
        'stock_actual', 'stock_minimo', 'estado'
    ]
    list_filter = ['categoria', 'estado']
    search_fields = ['codigo', 'nombre']
    list_editable = ['precio_venta', 'estado']
    ordering = ['nombre']
