"""Middleware: bloquea acciones de escritura con la licencia vencida/inexistente."""
from django.contrib import messages
from django.shortcuts import redirect

from .services import obtener_licencia

# Rutas donde NUNCA se bloquea (lectura, login, licencia, estáticos, admin).
RUTAS_PERMITIDAS = (
    '/acceder/', '/salir/', '/licencia/', '/static/', '/media/',
    '/admin/', '/healthz/', '/carta/',
)


class BloqueoLicenciaMiddleware:
    """Pone el sistema en modo solo lectura cuando la licencia está bloqueada.

    Cuando no hay licencia válida, cualquier POST hacia una ruta de negocio
    (cobrar, abrir/cerrar caja, crear pedidos, crear vendedores, ...) se
    rechaza con un mensaje. La lectura y las pantallas internas siguen
    operativas.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'POST' and request.path and not request.path.startswith(
                RUTAS_PERMITIDAS):
            licencia = obtener_licencia()
            if licencia['bloqueado']:
                messages.error(
                    request,
                    licencia['mensaje'] + ' El sistema está en modo solo lectura.',
                )
                destino = request.META.get('HTTP_REFERER') or '/'
                return redirect(destino)
        return self.get_response(request)