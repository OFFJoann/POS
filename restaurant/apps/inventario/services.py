"""
Servicios de la aplicación inventario.

Contiene la lógica de negocio para movimientos de inventario.
"""
from collections import defaultdict

from django.db import transaction
from .models import MovimientoInventario
from apps.productos.models import Producto


@transaction.atomic
def registrar_movimiento(producto, tipo, cantidad, motivo,
                         descripcion='', usuario=None):
    """
    Registra un movimiento de inventario y actualiza el stock.

    Para ventas se descuenta automáticamente.
    """
    stock_anterior = producto.stock_actual

    if tipo == 'entrada':
        producto.stock_actual += cantidad
    elif tipo in ('salida', 'venta'):
        producto.stock_actual -= cantidad
    elif tipo == 'ajuste':
        producto.stock_actual = cantidad

    producto.save()

    movimiento = MovimientoInventario.objects.create(
        producto=producto,
        tipo=tipo,
        cantidad=cantidad,
        stock_anterior=stock_anterior,
        stock_nuevo=producto.stock_actual,
        motivo=motivo,
        descripcion=descripcion,
        usuario=usuario,
    )
    return movimiento


@transaction.atomic
def descontar_inventario(producto, cantidad, pedido_id=None):
    """
    Descuenta inventario por una venta.
    Se llama automáticamente al facturar.
    """
    return registrar_movimiento(
        producto=producto,
        tipo='venta',
        cantidad=cantidad,
        motivo=f'Venta Pedido #{pedido_id}' if pedido_id else 'Venta',
        descripcion=f'Descuento automático por venta',
    )


def descontar_pedido(pedido):
    """
    Descuenta el inventario de un pedido al facturar.

    Si un detalle es un combo (``es_combo=True``), descuenta del inventario
    real cada uno de sus productos componentes multiplicado por la cantidad
    vendida del combo. Agrupa por producto para evitar movimientos duplicados.
    """
    movimientos = defaultdict(int)
    detalles = (
        pedido.detalles
        .select_related('producto')
        .prefetch_related('producto__componentes__producto')
        .all()
    )
    for detalle in detalles:
        producto = detalle.producto
        if getattr(producto, 'es_combo', False):
            for comp in producto.componentes.all():
                if comp.producto_id:
                    movimientos[comp.producto] += comp.cantidad * detalle.cantidad
        else:
            movimientos[producto] += detalle.cantidad

    for producto, cantidad in movimientos.items():
        descontar_inventario(producto, cantidad, pedido.id)
