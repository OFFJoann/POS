"""
Configuración del panel de administración para mesas.
"""
from django.contrib import admin
from .models import Mesa, Pedido, DetallePedido


class DetallePedidoInline(admin.TabularInline):
    """Detalles del pedido en línea."""
    model = DetallePedido
    extra = 0
    readonly_fields = ['producto', 'cantidad', 'precio_unitario', 'subtotal']


@admin.register(Mesa)
class MesaAdmin(admin.ModelAdmin):
    """Administración de mesas."""
    list_display = ['numero', 'estado', 'activa']
    list_filter = ['estado', 'activa']
    list_editable = ['estado', 'activa']
    ordering = ['numero']


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    """Administración de pedidos."""
    list_display = [
        'id', 'mesa', 'mesero', 'subtotal', 'total',
        'saldo_pendiente', 'estado', 'fecha_apertura'
    ]
    list_filter = ['estado', 'mesa']
    search_fields = ['mesa__numero', 'mesero__nombre']
    readonly_fields = ['subtotal', 'total', 'fecha_apertura', 'created_at']
    inlines = [DetallePedidoInline]
    ordering = ['-fecha_apertura']


@admin.register(DetallePedido)
class DetallePedidoAdmin(admin.ModelAdmin):
    """Administración de detalles de pedido."""
    list_display = ['pedido', 'producto', 'cantidad', 'precio_unitario', 'subtotal']
    search_fields = ['producto__nombre', 'pedido__id']
