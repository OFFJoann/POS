"""Sirve el dashboard React (build de `panel/dist`) desde Django.

El panel es una SPA, así que cualquier ruta interna (/panel/licencias,
/panel/configuracion) debe devolver el index.html y dejar que React Router
la resuelva en el navegador. Los archivos reales (JS/CSS con hash) los sirve
WhiteNoise antes de llegar aquí, así que el patrón es "atrapa todo".

Excepción: las rutas que parecen API (`/panel/api/...`) NO son de la SPA. La API
real vive en `/api/panel/`, así que si alguien escribe mal esa ruta no debe
recibir HTML con 200 (el cliente haría `res.json()` y se quedaría con `{}`).
Para eso se responde 404 en JSON, que es lo que un cliente espera.
"""

from django.conf import settings
from django.http import FileResponse, Http404, JsonResponse
from django.urls import re_path
from django.views.decorators.cache import never_cache

DIST = settings.PANEL_DIST


@never_cache
def dashboard(_request):
    indice = DIST / 'index.html'
    if not indice.exists():
        raise Http404(
            'El dashboard no está compilado. Ejecuta `npm ci && npm run build` '
            'dentro de licenses_server/panel.'
        )
    return FileResponse(indice.open('rb'), content_type='text/html')


@never_cache
def api_no_encontrada(request):
    return JsonResponse(
        {
            'ok': False,
            'error': 'Endpoint no encontrado. La API del panel está en /api/panel/.',
        },
        status=404,
    )


urlpatterns = [
    # Primero lo que parece API, para que no lo trague el catch-all de la SPA.
    re_path(r'^api(?:/.*)?$', api_no_encontrada, name='panel_api_404'),
    re_path(r'^.*$', dashboard, name='panel'),
]