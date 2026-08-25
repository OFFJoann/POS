"""
Context processors para la aplicación configuracion.

Inyecta la configuración de la empresa en todas las plantillas.
"""
from .models import Configuracion


def configuracion(request):
    """
    Context processor que expone la configuración de la empresa.

    Disponible en todas las plantillas como {{ configuracion }}.
    """
    return {'configuracion': Configuracion.obtener()}
