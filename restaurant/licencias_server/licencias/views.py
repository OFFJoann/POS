"""API pública de licencias y configuración del servidor central."""
import hashlib

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render

from .models import Licencia
from .services import construir_payload


def huella_secreto(secreto):
    """Huella corta (SHA-256) del secreto, para compararlo sin mostrarlo."""
    if not secreto:
        return ''
    return hashlib.sha256(secreto.encode()).hexdigest()[:12]


def api_licencia(request):
    """GET /api/licencia/?codigo=X → payload firmado de la licencia activa.

    Respuestas:
      - 200: {"ok": true, "licencia": {payload firmado}}
      - 400: falta el parámetro codigo
      - 404: codigo inexistente o licencia pausada
    """
    codigo = (request.GET.get('codigo') or '').strip()
    if not codigo:
        return JsonResponse({'ok': False, 'error': 'codigo requerido'}, status=400)

    licencia = Licencia.objects.filter(codigo=codigo, activa=True).first()
    if licencia is None:
        return JsonResponse({'ok': False, 'error': 'inexistente'}, status=404)

    return JsonResponse({'ok': True, 'licencia': construir_payload(licencia)})


def config_servidor(request):
    """Muestra el secreto compartido LICENCIA_SECRETO (solo superusuarios).

    Sirve para copiarlo al `.env` de cada POS (debe ser idéntico). Se muestra
    oculto con un botón "Mostrar", y también su huella corta para verificarla.
    """
    if not request.user.is_superuser:
        return JsonResponse({'detail': 'solo superusuarios'}, status=403)

    secreto = (settings.LICENCIA_SECRETO or '').strip()
    return render(request, 'licencias/configuracion_servidor.html', {
        'secreto': secreto,
        'hay_secreto': bool(secreto),
        'huella': huella_secreto(secreto),
        'total_licencias': Licencia.objects.count(),
        'licencias_activas': Licencia.objects.filter(activa=True).count(),
    })