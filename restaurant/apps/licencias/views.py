import hashlib

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render

from .services import obtener_licencia


def config_licencia_local(request):
    """Muestra el secreto local LICENCIA_SECRETO (solo superusuarios)."""
    if not request.user.is_superuser:
        return redirect('admin:index')

    secreto = (getattr(settings, 'LICENCIA_SECRETO', '') or '').strip()
    licencia = obtener_licencia(force=True)
    return render(request, 'licencias/configuracion_local.html', {
        'secreto': secreto,
        'hay_secreto': bool(secreto),
        'huella': hashlib.sha256(secreto.encode()).hexdigest()[:12] if secreto else '',
        'licencia': licencia,
    })


@login_required
def estado_licencia(request):
    """Página con el detalle de la licencia y botón para revalidar."""
    licencia = obtener_licencia(force=True)
    return render(request, 'licencias/estado_licencia.html', {
        'licencia': licencia,
    })


@login_required
def revalidar_licencia(request):
    """Reconsulta el servidor central y vuelve a la página de estado."""
    if request.method == 'POST':
        licencia = obtener_licencia(force=True)
        messages.success(request, licencia['mensaje'])
    return redirect('estado_licencia')