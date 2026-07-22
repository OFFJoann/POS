"""
Context processors para la aplicación ventas.

Proporciona variables globales a todas las plantillas.
"""
from apps.caja.models import AperturaCaja


def caja_abierta(request):
    """
    Context processor que indica si hay una caja abierta.

    Disponible en todas las plantillas como {{ caja_abierta }}.
    """
    if request.user.is_authenticated:
        caja = AperturaCaja.objects.filter(activa=True).first()
        return {'caja_abierta': caja}
    return {'caja_abierta': None}
