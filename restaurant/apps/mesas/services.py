"""
Servicios de la aplicación mesas.

Contiene la lógica de negocio para gestión de mesas y pedidos.
"""
from django.db import transaction
from django.utils import timezone
from .models import Mesa, Pedido, DetallePedido
from apps.productos.models import Producto


def obtener_mesas_con_estado():
    """Retorna todas las mesas activas con su estado actual."""
    return Mesa.objects.filter(activa=True).order_by('numero')


def cambiar_estado_mesa(mesa, nuevo_estado):
    """Cambia el estado de una mesa."""
    mesa.estado = nuevo_estado
    mesa.save()
    return mesa


def crear_pedido(mesa, mesero):
    """
    Crea un nuevo pedido para una mesa.

    Cambia la mesa a estado 'activo' y cierra pedidos anteriores.
    """
    Pedido.objects.filter(mesa=mesa, estado='activo').update(estado='cerrado')
    pedido = Pedido.objects.create(
        mesa=mesa,
        mesero=mesero,
        estado='activo',
    )
    if mesa.estado == 'libre':
        mesa.estado = 'activo'
        mesa.save()
    return pedido


@transaction.atomic
def agregar_producto_a_pedido(pedido, producto_id, cantidad=1, cortesia=False, precio_personalizado=None):
    """
    Agrega un producto al pedido o incrementa su cantidad
    si ya existe.

    Si cortesia=True, el precio se pone en 0 y se marca como cortesía.
    Si precio_personalizado se especifica, se usa ese precio en lugar
    del precio de venta del producto.
    """
    producto = Producto.objects.get(pk=producto_id)
    if cortesia:
        precio = 0
    elif precio_personalizado is not None:
        precio = precio_personalizado
    else:
        precio = producto.precio_venta
    detalle, creado = DetallePedido.objects.get_or_create(
        pedido=pedido,
        producto=producto,
        es_cortesia=cortesia,
        precio_unitario=precio,
        defaults={
            'cantidad': cantidad,
            'subtotal': precio * cantidad,
        }
    )
    if not creado:
        detalle.cantidad += cantidad
        detalle.precio_unitario = precio
        detalle.subtotal = detalle.cantidad * precio
        detalle.save()

    pedido.calcular_totales()
    return detalle


@transaction.atomic
def modificar_cantidad(detalle_id, nueva_cantidad):
    """Modifica la cantidad de un producto en el pedido."""
    detalle = DetallePedido.objects.get(pk=detalle_id)
    detalle.cantidad = nueva_cantidad
    detalle.subtotal = detalle.cantidad * detalle.precio_unitario
    detalle.save()
    detalle.pedido.calcular_totales()
    return detalle


@transaction.atomic
def eliminar_detalle(detalle_id):
    """Elimina un producto del pedido."""
    detalle = DetallePedido.objects.get(pk=detalle_id)
    pedido = detalle.pedido
    detalle.delete()
    pedido.calcular_totales()
    return pedido


@transaction.atomic
def aplicar_descuento(pedido, descuento):
    """Aplica un descuento al pedido."""
    pedido.descuento = descuento
    pedido.calcular_totales()
    return pedido


def cerrar_pedido(pedido):
    """Cierra un pedido y actualiza el estado de la mesa."""
    pedido.estado = 'cerrado'
    pedido.fecha_cierre = timezone.now()
    pedido.save()
    mesa = pedido.mesa
    mesa.estado = 'libre'
    mesa.save()
    return pedido
