"""
Decoradores para control de acceso y permisos.
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def admin_required(view_func):
    """
    Decorador que permite acceso solo a administradores.

    Un usuario es administrador si tiene is_staff=True o es superuser.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('acceder')
        if not request.user.is_staff:
            messages.error(request, 'No tienes permisos para realizar esta acción.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def vendedor_required(view_func):
    """
    Decorador que permite acceso solo a vendedores activos.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('acceder')
        if not hasattr(request.user, 'vendedor'):
            messages.error(request, 'Perfil de vendedor no encontrado.')
            return redirect('acceder')
        if not request.user.vendedor.activo:
            messages.error(request, 'Tu cuenta está inactiva.')
            return redirect('acceder')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
