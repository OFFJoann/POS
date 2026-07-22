"""
Servicios de la aplicación usuarios.

Contiene la lógica de negocio para la gestión de vendedores.
"""
from django.contrib.auth.models import User
from .models import Vendedor


def crear_vendedor(nombre, apellidos, cedula, telefono='', activo=True):
    """
    Crea un nuevo vendedor con su usuario Django asociado.
    """
    user = User.objects.create_user(
        username=cedula,
        first_name=nombre,
        last_name=apellidos,
    )
    vendedor = Vendedor.objects.create(
        usuario=user,
        nombre=nombre,
        apellidos=apellidos,
        cedula=cedula,
        telefono=telefono,
        activo=activo,
    )
    return vendedor


def actualizar_vendedor(vendedor, datos):
    """
    Actualiza los datos de un vendedor y su usuario asociado.
    """
    for campo, valor in datos.items():
        setattr(vendedor, campo, valor)
    vendedor.save()
    return vendedor


def desactivar_vendedor(vendedor):
    """
    Desactiva un vendedor (no lo elimina físicamente).
    """
    vendedor.activo = False
    vendedor.usuario.is_active = False
    vendedor.usuario.save()
    vendedor.save()
    return vendedor
