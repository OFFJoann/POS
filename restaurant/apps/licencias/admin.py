"""Admin de solo lectura del estado de licencia en el POS.

Permite ver el secreto local (LICENCIA_SECRETO) y su huella para mapearlo
con el del servidor central.
"""
import hashlib

from django.conf import settings
from django.contrib import admin
from django.urls import path
from django.utils.html import format_html

from .models import EstadoLicencia
from .views import config_licencia_local


def _secreto():
    return (getattr(settings, 'LICENCIA_SECRETO', '') or '').strip()


def _huella_secreto():
    """Huella corta del secreto local, para compararla con el servidor."""
    secreto = _secreto()
    if not secreto:
        return '(sin secreto)'
    return hashlib.sha256(secreto.encode()).hexdigest()[:12]


@admin.register(EstadoLicencia)
class EstadoLicenciaAdmin(admin.ModelAdmin):
    """Solo lectura: la licencia se administra en el servidor central."""

    change_list_template = 'licencias/estado_change_list.html'
    list_display = (
        'codigo', 'cliente', 'vigencia_hasta', 'estado_actual',
        'limite_vendedores', 'secreto_local', 'actualizada_en',
    )
    readonly_fields = (
        'codigo', 'cliente', 'vigencia_hasta', 'limite_vendedores',
        'features', 'firma', 'datos', 'actualizada_en',
        'estado_actual', 'secreto_local', 'huella_secreto',
    )
    fields = readonly_fields

    def get_urls(self):
        return [
            path(
                'configuracion/',
                self.admin_site.admin_view(config_licencia_local),
                name='licencias_config_local',
            ),
        ] + super().get_urls()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description='Estado')
    def estado_actual(self, obj):
        from .services import obtener_licencia
        return obtener_licencia()['estado']

    @admin.display(description='Huella del secreto')
    def huella_secreto(self, obj):
        return _huella_secreto()

    @admin.display(description='LICENCIA_SECRETO (local)')
    def secreto_local(self, obj):
        secreto = _secreto()
        if not secreto:
            return format_html('<strong>NO CONFIGURADO</strong>')
        return format_html(
            '<code id="secreto" data-secreto="{}">'
            '----------------------------</code> '
            '<button type="button" class="button" id="btn-secreto">Mostrar</button>',
            secreto,
        )