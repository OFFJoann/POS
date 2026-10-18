"""Registro de los modelos de créditos en el admin de Django."""
from django.contrib import admin

from .models import Abono, Cliente, Credito, Cuota


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'correo', 'cedula', 'telefono', 'saldo_total')
    search_fields = ('nombre', 'correo', 'cedula')


class CuotaInline(admin.TabularInline):
    model = Cuota
    extra = 0
    readonly_fields = ('numero', 'fecha_vencimiento', 'monto', 'estado',
                       'fecha_pago')
    can_delete = False


@admin.register(Credito)
class CreditoAdmin(admin.ModelAdmin):
    list_display = ('factura', 'cliente', 'monto_total', 'saldo_pendiente',
                    'cuotas_total', 'estado', 'creado_en')
    list_filter = ('estado',)
    search_fields = ('cliente__nombre', 'factura__numero')
    inlines = (CuotaInline,)


@admin.register(Abono)
class AbonoAdmin(admin.ModelAdmin):
    list_display = ('credito', 'monto', 'metodo', 'usuario', 'creado_en')
    list_filter = ('metodo',)
    search_fields = ('credito__cliente__nombre',)
