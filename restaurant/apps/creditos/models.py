"""
Modelos de la aplicación créditos.

Un crédito nace al cobrar una venta con método de pago "crédito": la venta se
registra ese día (factura + pago) y, en paralelo, se crea un Credito con su
calendario de Cuotas (sin interés). El cliente va abonando; los Abonos se
guardan en su modelo propio para que NO sumen al cierre de caja.
"""
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Cliente(models.Model):
    """Cliente dueño de uno o más créditos."""
    nombre = models.CharField('Nombre', max_length=150, db_index=True)
    cedula = models.CharField('Cédula', max_length=20, blank=True, default='',
        db_index=True)
    correo = models.EmailField('Correo', blank=True, default='')
    telefono = models.CharField('Teléfono', max_length=30, blank=True, default='')
    creado_en = models.DateTimeField('Creado', auto_now_add=True)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['nombre']),
            models.Index(fields=['cedula']),
        ]

    def __str__(self):
        return self.nombre

    @property
    def saldo_total(self):
        """Suma de lo que debe en todos sus créditos activos."""
        return sum(
            (c.saldo_pendiente for c in self.creditos.filter(estado='activo')),
            Decimal('0'),
        )


class Credito(models.Model):
    """Crédito otorgado a un cliente para una factura."""
    ESTADOS = [
        ('activo', 'Activo'),
        ('pagado', 'Pagado'),
        ('vencido', 'Vencido'),
    ]

    factura = models.OneToOneField(
        'ventas.Factura', on_delete=models.PROTECT,
        related_name='credito', verbose_name='Factura'
    )
    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT,
        related_name='creditos', verbose_name='Cliente'
    )
    FRECUENCIAS = [
        ('mensual', 'Mensual'),
        ('quincenal', 'Quincenal'),
    ]
    cuotas_total = models.PositiveIntegerField('Cuotas', default=1)
    frecuencia = models.CharField('Frecuencia', max_length=20,
        choices=FRECUENCIAS, default='mensual')
    monto_total = models.DecimalField('Monto total', max_digits=12, decimal_places=2)
    saldo_pendiente = models.DecimalField('Saldo pendiente', max_digits=12,
        decimal_places=2)
    estado = models.CharField('Estado', max_length=20, choices=ESTADOS,
        default='activo', db_index=True)
    observaciones = models.TextField('Observaciones', blank=True, default='')
    creado_en = models.DateTimeField('Creado', auto_now_add=True)

    class Meta:
        verbose_name = 'Crédito'
        verbose_name_plural = 'Créditos'
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['creado_en']),
        ]

    def __str__(self):
        return f'Crédito {self.cliente} - ${self.saldo_pendiente}'

    @property
    def monto_pagado(self):
        return self.monto_total - self.saldo_pendiente

    @property
    def cuotas_pendientes(self):
        """Cuotas abiertas (sin pagar o pagadas parcialmente)."""
        return self.cuotas.exclude(estado='pagada').count()

    @property
    def cuotas_pagadas(self):
        return self.cuotas.filter(estado='pagada').count()

    @property
    def cuotas_parciales(self):
        return self.cuotas.filter(estado='parcial').count()

    @property
    def cuotas_vencidas(self):
        return self.cuotas.filter(
            estado='pendiente', fecha_vencimiento__lt=timezone.localdate()
        ).count()

    @property
    def saldo_vencido(self):
        """Suma de las cuotas pendientes ya vencidas (lo atrasado)."""
        total = self.cuotas.filter(
            estado='pendiente', fecha_vencimiento__lt=timezone.localdate()
        ).aggregate(total=models.Sum('monto'))['total'] or Decimal('0')
        return total

    @property
    def proxima_cuota(self):
        return self.cuotas.exclude(estado='pagada').order_by('numero').first()

    @property
    def porcentaje_pagado(self):
        if self.monto_total <= 0:
            return Decimal('0')
        return (self.monto_pagado / self.monto_total * 100).quantize(
            Decimal('0.1'), ROUND_HALF_UP)

    def recalcular_estado(self):
        """Ajusta el estado a partir de las cuotas y el saldo."""
        if self.saldo_pendiente <= 0:
            self.estado = 'pagado'
        elif self.cuotas_vencidas > 0:
            self.estado = 'vencido'
        else:
            self.estado = 'activo'
        self.save(update_fields=['estado'])
        return self.estado


class Cuota(models.Model):
    """Una cuota del calendario de un crédito.

    `monto_pagado` acumula lo abonado contra esta cuota, por lo que puede
    quedar 'pendiente' (nada), 'parcial' (algo) o 'pagada' (completa).
    """
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('parcial', 'Parcial'),
        ('pagada', 'Pagada'),
    ]

    credito = models.ForeignKey(
        Credito, on_delete=models.CASCADE,
        related_name='cuotas', verbose_name='Crédito'
    )
    numero = models.PositiveIntegerField('Número')
    fecha_vencimiento = models.DateField('Vencimiento', db_index=True)
    monto = models.DecimalField('Monto', max_digits=12, decimal_places=2)
    monto_pagado = models.DecimalField('Abonado', max_digits=12, decimal_places=2,
        default=0)
    estado = models.CharField('Estado', max_length=20, choices=ESTADOS,
        default='pendiente', db_index=True)
    fecha_pago = models.DateField('Fecha de pago', null=True, blank=True)
    aviso_antes_enviado = models.BooleanField('Aviso previo enviado',
        default=False,
        help_text='Recordatorio enviado un día antes del vencimiento.')
    aviso_vencimiento_enviado = models.BooleanField('Aviso de vencimiento enviado',
        default=False,
        help_text='Recordatorio enviado el día del vencimiento.')

    class Meta:
        verbose_name = 'Cuota'
        verbose_name_plural = 'Cuotas'
        ordering = ['numero']
        unique_together = [('credito', 'numero')]
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['fecha_vencimiento']),
        ]

    def __str__(self):
        return f'Cuota {self.numero} - ${self.monto}'

    @property
    def monto_faltante(self):
        """Lo que falta por pagar de esta cuota."""
        falta = self.monto - self.monto_pagado
        return falta if falta > 0 else Decimal('0')

    @property
    def esta_vencida(self):
        return (self.estado != 'pagada'
                and self.fecha_vencimiento < timezone.localdate())

    @property
    def esta_pagada(self):
        return self.estado == 'pagada'


class Abono(models.Model):
    """Pago parcial o total que hace el cliente contra su crédito.

    Vive en su modelo propio (no en `ventas.Pago`) para que quede fuera del
    cierre de caja: el dinero de la venta ya se contabilizó el día del crédito.
    """
    METODOS = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
    ]

    credito = models.ForeignKey(
        Credito, on_delete=models.CASCADE,
        related_name='abonos', verbose_name='Crédito'
    )
    cuota = models.ForeignKey(
        Cuota, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='abonos',
        verbose_name='Cuota'
    )
    monto = models.DecimalField('Monto', max_digits=12, decimal_places=2)
    metodo = models.CharField('Método', max_length=20, choices=METODOS,
        default='efectivo')
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name='Usuario'
    )
    observacion = models.CharField('Nota', max_length=200, blank=True, default='')
    creado_en = models.DateTimeField('Fecha', auto_now_add=True)

    class Meta:
        verbose_name = 'Abono'
        verbose_name_plural = 'Abonos'
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['creado_en']),
            models.Index(fields=['metodo']),
        ]

    def __str__(self):
        return f'Abono ${self.monto} - {self.credito.cliente}'
