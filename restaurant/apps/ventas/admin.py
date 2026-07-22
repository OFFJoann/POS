"""
Configuración del panel de administración para ventas.
"""
from django.contrib import admin
from .models import Factura, Pago


class PagoInline(admin.TabularInline):
    """Pagos en línea dentro de factura."""
    model = Pago
    extra = 0
    readonly_fields = ['metodo', 'monto', 'created_at']


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    """Administración de facturas."""
    list_display = [
        'numero', 'mesa', 'mesero', 'metodo_pago',
        'total', 'es_parcial', 'created_at'
    ]
    list_filter = ['metodo_pago', 'es_parcial', 'created_at']
    search_fields = ['numero', 'mesa__numero', 'mesero__nombre']
    readonly_fields = ['numero', 'created_at']
    inlines = [PagoInline]
    ordering = ['-numero']


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    """Administración de pagos."""
    list_display = ['factura', 'metodo', 'monto', 'usuario', 'created_at']
    list_filter = ['metodo', 'created_at']
    search_fields = ['factura__numero']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
