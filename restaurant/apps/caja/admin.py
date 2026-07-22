"""
Configuración del panel de administración para caja.
"""
from django.contrib import admin
from .models import AperturaCaja, Egreso, CategoriaEgreso


class EgresoInline(admin.TabularInline):
    """Egresos en línea dentro de caja."""
    model = Egreso
    extra = 0
    readonly_fields = ['valor', 'motivo', 'usuario', 'created_at']


@admin.register(AperturaCaja)
class AperturaCajaAdmin(admin.ModelAdmin):
    """Administración de aperturas de caja."""
    list_display = [
        'id', 'usuario', 'monto_inicial', 'activa',
        'fecha_apertura', 'fecha_cierre'
    ]
    list_filter = ['activa', 'fecha_apertura']
    search_fields = ['usuario__username']
    readonly_fields = ['fecha_apertura']
    inlines = [EgresoInline]
    ordering = ['-fecha_apertura']


@admin.register(CategoriaEgreso)
class CategoriaEgresoAdmin(admin.ModelAdmin):
    """Administración de categorías de egreso."""
    list_display = ['nombre']
    search_fields = ['nombre']


@admin.register(Egreso)
class EgresoAdmin(admin.ModelAdmin):
    """Administración de egresos."""
    list_display = ['motivo', 'categoria', 'valor', 'usuario', 'created_at']
    list_filter = ['created_at', 'categoria']
    search_fields = ['motivo', 'descripcion']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
