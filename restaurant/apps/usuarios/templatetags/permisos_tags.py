"""Filtros de template para permisos granulares."""
from django import template

register = template.Library()


@register.filter(name='puede')
def puede(user, codigo):
    """Devuelve True si el usuario tiene el permiso dado.

    Uso en plantillas: {{ user|puede:"facturar" }}
    Los administradores (is_staff/is_superuser) siempre devuelven True.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
        return True
    vendedor = getattr(user, 'vendedor', None)
    if not vendedor:
        return False
    return vendedor.puede(codigo)
