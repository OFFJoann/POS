"""
Servicios de la aplicación inventario.

Contiene la lógica de negocio para movimientos de inventario.
"""
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
