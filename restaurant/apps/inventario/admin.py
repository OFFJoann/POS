"""
Configuración del panel de administración para inventario.
"""
from django.contrib import admin
from .models import MovimientoInventario


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    """Administración de movimientos de inventario."""
    list_display = [
        'producto', 'tipo', 'cantidad',
        'stock_anterior', 'stock_nuevo', 'motivo', 'usuario', 'created_at'
    ]
    list_filter = ['tipo', 'created_at']
    search_fields = ['producto__nombre', 'producto__codigo', 'motivo']
    readonly_fields = ['stock_anterior', 'stock_nuevo', 'created_at']
    ordering = ['-created_at']
