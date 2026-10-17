"""Quién puede qué en el panel de licencias.

Solo hay dos roles: administrador y visualizador. La diferencia está en las
escrituras; leer el panel es igual para los dos. El secreto compartido queda
reservado al administrador, porque quien lo tenga puede emitir licencias por su
cuenta y saltarse este panel por completo.

El permiso se comprueba aquí, en el servidor, para todas las peticiones. Ocultar
botones en la interfaz es solo comodidad: no es lo que protege las licencias.
"""
from functools import wraps

from django.http import JsonResponse

from .models import UsuarioPanel

# `GET` y `HEAD` no cambian nada; todo lo demás sí.
METODOS_ESCRITURA = {'POST', 'PUT', 'PATCH', 'DELETE'}

ROL_ADMINISTRADOR = UsuarioPanel.ADMINISTRADOR
ROL_VISUALIZADOR = UsuarioPanel.VISUALIZADOR


def error_json(mensaje, status=400):
    return JsonResponse({'ok': False, 'error': mensaje}, status=status)


def rol_de(usuario):
    """Devuelve 'administrador', 'visualizador' o None si no tiene acceso.

    None significa que la cuenta existe pero no está autorizada para el panel:
    así un superusuario creado sin ficha no entra por la puerta de atrás.
    """
    if not usuario or not usuario.is_authenticated:
        return None
    if not usuario.is_active:
        return None
    perfil = getattr(usuario, 'panel', None)
    if perfil is not None:
        return perfil.rol
    # Sin ficha, los superusuarios previos siguen siendo administradores: si la
    # migración se aplicara a medias, nadie se queda fuera de su propio panel.
    if usuario.is_superuser:
        return ROL_ADMINISTRADOR
    return None


def puede_escribir(rol):
    return rol == ROL_ADMINISTRADOR


def requiere_panel(vista):
    """Deja pasar a quien tenga rol; corta las escrituras a los visualizadores.

    Un mismo decorador para leer y escribir: se decide por el método, así no
    queda ninguna vista de escritura por proteger y es imposible olvidar
    añadirla a una lista aparte.
    """
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        usuario = request.user
        if not usuario.is_authenticated:
            return error_json('Sesión expirada', 401)
        rol = rol_de(usuario)
        if rol is None:
            return error_json('El usuario no tiene acceso al panel', 403)
        if request.method in METODOS_ESCRITURA and not puede_escribir(rol):
            return error_json(
                'Tu cuenta es solo de lectura. Pide a un administrador que la cambie.',
                403)
        return vista(request, *args, **kwargs)
    return envoltura