"""
Signals de la aplicación ventas.

Señales para descontar inventario automáticamente
al generar una factura.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Factura, Pago
from apps.inventario.services import descontar_inventario


@receiver(post_save, sender=Factura)
def descontar_inventario_al_facturar(sender, instance, created, **kwargs):
    """
    Signal que descuenta el inventario cuando se crea una factura.

    Solo descuenta si no es un pago parcial (el inventario se
    descuenta completo en el primer pago).
    """
    if created and not instance.es_parcial and not getattr(instance, '_skip_inventory_deduction', False):
        pedido = instance.pedido
        for detalle in pedido.detalles.select_related('producto').all():
            descontar_inventario(
                producto=detalle.producto,
                cantidad=detalle.cantidad,
                pedido_id=pedido.id,
            )
