"""Inyecta el estado de licencia en todas las plantillas.

Uso en templates: {{ licencia.estado }}, {{ licencia.color }},
{{ licencia.mensaje }}, {% if licencia.bloqueado %} ...
"""
from .services import obtener_licencia


def licencia(request):
    return {'licencia': obtener_licencia()}