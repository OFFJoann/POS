"""
Servicios de la aplicación mesas.

Contiene la lógica de negocio para gestión de mesas y pedidos.
"""
from decimal import Decimal

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
    # Si ya existe un detalle AÚN NO enviado a caja para este producto, se
    # incrementa su cantidad. Si el detalle existente ya fue enviado
    # (solicitud distinto de NULL, pendiente o atendida), se crea un detalle
    # nuevo para la adición, para que "Solicitar en caja" envíe únicamente lo
    # nuevo y no reenvíe lo que ya está atendido en caja.
    detalle = DetallePedido.objects.filter(
        pedido=pedido,
        producto=producto,
        es_cortesia=cortesia,
        precio_unitario=precio,
        solicitud__isnull=True,
    ).first()
    if detalle:
        detalle.cantidad += cantidad
        detalle.subtotal = detalle.cantidad * precio
        detalle.save()
    else:
        detalle = DetallePedido.objects.create(
            pedido=pedido,
            producto=producto,
            es_cortesia=cortesia,
            precio_unitario=precio,
            cantidad=cantidad,
            subtotal=precio * cantidad,
        )

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
def actualizar_cantidad_detalle(detalle, nueva_cantidad):
    """Actualiza la cantidad de un detalle respetando lo ya enviado a caja.

    - Detalle aún no enviado (solicitud NULL): se cambia su cantidad directo.
    - Detalle YA enviado y se aumenta: la diferencia se guarda en un detalle
      nuevo sin enviar, para que "Solicitar en caja" mande solo el agregado.
    - Se reduce o elimina: se aplica sobre el detalle original.
    """
    nueva = Decimal(str(nueva_cantidad))
    if nueva <= 0:
        pedido = detalle.pedido
        detalle.delete()
        pedido.calcular_totales()
        return None

    if detalle.solicitud is None:
        detalle.cantidad = nueva
        detalle.subtotal = detalle.cantidad * detalle.precio_unitario
        detalle.save()
        detalle.pedido.calcular_totales()
        return detalle

    if nueva > detalle.cantidad:
        delta = nueva - detalle.cantidad
        existente = DetallePedido.objects.filter(
            pedido=detalle.pedido,
            producto=detalle.producto,
            es_cortesia=detalle.es_cortesia,
            precio_unitario=detalle.precio_unitario,
            solicitud__isnull=True,
        ).exclude(pk=detalle.pk).first()
        if existente:
            existente.cantidad += delta
            existente.subtotal = existente.cantidad * existente.precio_unitario
            existente.save()
        else:
            DetallePedido.objects.create(
                pedido=detalle.pedido,
                producto=detalle.producto,
                es_cortesia=detalle.es_cortesia,
                precio_unitario=detalle.precio_unitario,
                cantidad=delta,
                subtotal=detalle.precio_unitario * delta,
            )
        detalle.pedido.calcular_totales()
        return detalle

    detalle.cantidad = nueva
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
