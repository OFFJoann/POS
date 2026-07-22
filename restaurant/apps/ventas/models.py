"""
Modelos de la aplicación ventas.

Gestiona facturación, pagos y métodos de pago.
"""
from django.db import models
from django.conf import settings


class Factura(models.Model):
    """
    Factura generada al pagar un pedido.

    Cada factura tiene un número consecutivo único.
    """
    METODOS_PAGO = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('cortesia', 'Cortesía'),
    ]

    numero = models.PositiveIntegerField(
        'Número de factura', unique=True,
        db_index=True,
        help_text='Número consecutivo de factura'
    )
    pedido = models.OneToOneField(
        'mesas.Pedido', on_delete=models.PROTECT,
        related_name='factura',
        verbose_name='Pedido'
    )
    mesa = models.ForeignKey(
        'mesas.Mesa', on_delete=models.PROTECT,
        related_name='facturas',
        verbose_name='Mesa'
    )
    mesero = models.ForeignKey(
        'usuarios.Vendedor', on_delete=models.PROTECT,
        related_name='facturas',
        verbose_name='Mesero'
    )
    metodo_pago = models.CharField(
        'Método de pago', max_length=20,
        choices=METODOS_PAGO, db_index=True
    )
    subtotal = models.DecimalField('Subtotal', max_digits=12, decimal_places=2)
    descuento = models.DecimalField('Descuento', max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField('Total', max_digits=12, decimal_places=2)
    valor_recibido = models.DecimalField(
        'Valor recibido', max_digits=12, decimal_places=2,
        default=0
    )
    cambio = models.DecimalField(
        'Cambio', max_digits=12, decimal_places=2, default=0
    )
    es_parcial = models.BooleanField('Pago parcial', default=False)
    saldo_pendiente = models.DecimalField(
        'Saldo pendiente', max_digits=12, decimal_places=2,
        default=0
    )
    created_at = models.DateTimeField('Fecha', auto_now_add=True)

    class Meta:
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'
        ordering = ['-numero']
        indexes = [
            models.Index(fields=['numero']),
            models.Index(fields=['metodo_pago']),
            models.Index(fields=['created_at']),
            models.Index(fields=['mesero']),
            models.Index(fields=['mesa']),
        ]

    def __str__(self):
        return f'Factura #{self.numero} - Mesa {self.mesa.numero}'

    @property
    def hora(self):
        """Retorna la hora de creación."""
        return self.created_at.strftime('%H:%M:%S')


class Pago(models.Model):
    """
    Registro de pago individual.

    Permite pagos parciales y completos.
    """
    METODOS = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('cortesia', 'Cortesía'),
    ]

    factura = models.ForeignKey(
        Factura, on_delete=models.CASCADE,
        related_name='pagos',
        verbose_name='Factura'
    )
    pedido = models.ForeignKey(
        'mesas.Pedido', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='pagos',
        verbose_name='Pedido'
    )
    metodo = models.CharField(
        'Método', max_length=20, choices=METODOS,
        db_index=True
    )
    monto = models.DecimalField('Monto', max_digits=12, decimal_places=2)
    valor_recibido = models.DecimalField(
        'Valor recibido', max_digits=12, decimal_places=2,
        default=0
    )
    cambio = models.DecimalField(
        'Cambio', max_digits=12, decimal_places=2, default=0
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name='Usuario'
    )
    created_at = models.DateTimeField('Fecha', auto_now_add=True)

    class Meta:
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['metodo']),
            models.Index(fields=['factura']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'Pago {self.get_metodo_display()} - ${self.monto}'
