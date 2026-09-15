"""
Backend de autenticación personalizado.

Permite iniciar sesión con correo y contraseña.
"""
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from .models import Vendedor


class EmailBackend(BaseBackend):
    """
    Autenticación mediante correo y contraseña.

    Busca el User asociado a un Vendedor por su email y valida la contraseña.
    El vendedor debe estar activo.
    """

    def authenticate(self, request, email=None, password=None, **kwargs):
        """Autentica un usuario por su email y contraseña."""
        if not email or not password:
            return None
        try:
            vendedor = Vendedor.objects.get(email__iexact=email)
        except (Vendedor.DoesNotExist, Vendedor.MultipleObjectsReturned):
            return None
        if not vendedor.activo:
            return None
        user = vendedor.usuario
        if not user.is_active:
            return None
        if not check_password(password, user.password):
            return None
        return user

    def get_user(self, user_id):
        """Obtiene un usuario por su ID."""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None