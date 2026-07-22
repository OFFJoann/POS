"""
Backend de autenticación personalizado.

Permite iniciar sesión únicamente con el número de cédula.
No requiere contraseña.
"""
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from .models import Vendedor


class CedulaBackend(BaseBackend):
    """
    Autenticación mediante cédula.

    Busca un vendedor por su cédula y retorna el usuario
    asociado si está activo.
    """

    def authenticate(self, request, cedula=None):
        """Autentica un usuario por su cédula."""
        try:
            vendedor = Vendedor.objects.get(cedula=cedula, activo=True)
            return vendedor.usuario
        except Vendedor.DoesNotExist:
            return None

    def get_user(self, user_id):
        """Obtiene un usuario por su ID."""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
