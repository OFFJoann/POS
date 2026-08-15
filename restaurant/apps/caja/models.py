"""
Modelos de la aplicación caja.

Gestiona apertura, cierre y egresos de caja.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class AperturaCaja(models.Model):
    """
    Registro de apertura de caja.

    Solo puede haber una caja abierta a la vez.
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        verbose_name='Usuario'
    )
    fecha_apertura = models.DateTimeField('Fecha apertura', auto_now_add=True)
    fecha_cierre = models.DateTimeField('Fecha cierre', null=True, blank=True)
    activa = models.BooleanField('Activa', default=True)

    class Meta:
        verbose_name = 'Apertura de caja'
        verbose_name_plural = 'Aperturas de caja'
        ordering = ['-fecha_apertura']

    def __str__(self):
        estado = 'Abierta' if self.activa else 'Cerrada'
        return f'Caja {estado} - {self.fecha_apertura.strftime("%d/%m/%Y %H:%M")}'

    @property
    def _fecha_fin(self):
        """Retorna la fecha de cierre o la fecha actual si está abierta."""
        return self.fecha_cierre or timezone.now()

    @property
    def total_ventas_efectivo(self):
        """Suma de todas las ventas en efectivo durante esta caja."""
        from apps.ventas.models import Pago
        total = Pago.objects.filter(
            metodo='efectivo',
            created_at__gte=self.fecha_apertura,
            created_at__lte=self._fecha_fin,
        ).aggregate(total=models.Sum('monto'))['total'] or 0
        return total

    @property
    def total_ventas_transferencia(self):
        """Suma de todas las ventas por transferencia."""
        from apps.ventas.models import Pago
        total = Pago.objects.filter(
            metodo='transferencia',
            created_at__gte=self.fecha_apertura,
            created_at__lte=self._fecha_fin,
        ).aggregate(total=models.Sum('monto'))['total'] or 0
        return total

    @property
    def total_ventas(self):
        """Total de ventas."""
        return self.total_ventas_efectivo + self.total_ventas_transferencia

    @property
    def total_egresos(self):
        """Suma de egresos registrados durante esta caja."""
        total = self.egresos.aggregate(total=models.Sum('valor'))['total'] or 0
        return total

    @property
    def total_egresos_efectivo(self):
        """Egresos pagados en efectivo."""
        total = self.egresos.filter(metodo_pago='efectivo').aggregate(
            total=models.Sum('valor')
        )['total'] or 0
        return total

    @property
    def total_egresos_transferencia(self):
        """Egresos pagados por transferencia."""
        total = self.egresos.filter(metodo_pago='transferencia').aggregate(
            total=models.Sum('valor')
        )['total'] or 0
        return total

    @property
    def dinero_esperado(self):
        """Total: ventas (efectivo+transferencia) - egresos."""
        return self.total_ventas - self.total_egresos

    @property
    def diferencia(self):
        """Diferencia entre lo esperado y lo real."""
        return self.total_ventas - self.total_egresos


class CierreCaja(models.Model):
    """
    Registro de cierre de caja con resumen consolidado del día.

    Se crea automáticamente al cerrar una AperturaCaja.
    Almacena el resumen de ventas, egresos y dinero esperado
    para consulta histórica.
    """
    caja = models.ForeignKey(
        AperturaCaja, on_delete=models.CASCADE,
        related_name='cierres',
        verbose_name='Caja'
    )
    fecha_cierre = models.DateTimeField('Fecha de cierre', auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name='Usuario'
    )
    monto_inicial = models.DecimalField(
        'Monto inicial', max_digits=12, decimal_places=2, default=0
    )
    total_ventas_efectivo = models.DecimalField(
        'Ventas en efectivo', max_digits=12, decimal_places=2, default=0
    )
    total_ventas_transferencia = models.DecimalField(
        'Ventas por transferencia', max_digits=12, decimal_places=2, default=0
    )
    total_ventas = models.DecimalField(
        'Total ventas', max_digits=12, decimal_places=2, default=0
    )
    total_egresos = models.DecimalField(
        'Total egresos', max_digits=12, decimal_places=2, default=0
    )
    total_egresos_efectivo = models.DecimalField(
        'Egresos en efectivo', max_digits=12, decimal_places=2, default=0
    )
    total_egresos_transferencia = models.DecimalField(
        'Egresos por transferencia', max_digits=12, decimal_places=2, default=0
    )
    dinero_esperado = models.DecimalField(
        'Dinero esperado', max_digits=12, decimal_places=2, default=0
    )
    efectivo_conteo = models.DecimalField(
        'Efectivo contado', max_digits=12, decimal_places=2, default=0,
        help_text='Efectivo físico contado al cerrar la caja'
    )
    diferencia = models.DecimalField(
        'Diferencia', max_digits=12, decimal_places=2, default=0
    )
    observaciones = models.TextField('Observaciones', blank=True)

    class Meta:
        verbose_name = 'Cierre de caja'
        verbose_name_plural = 'Cierres de caja'
        ordering = ['-fecha_cierre']

    def __str__(self):
        return f'Cierre {self.fecha_cierre.strftime("%d/%m/%Y")} - ${self.dinero_esperado:0f}'

    @property
    def facturas_del_dia(self):
        """Retorna las facturas generadas entre la apertura y cierre de esta caja."""
        from apps.ventas.models import Factura
        return Factura.objects.filter(
            created_at__gte=self.caja.fecha_apertura,
            created_at__lte=self.fecha_cierre,
        ).order_by('-numero')


class CategoriaEgreso(models.Model):
    """
    Categoría para clasificar egresos.
    Ejemplo: Arriendo, Servicios, Surtido, etc.
    """
    nombre = models.CharField('Nombre', max_length=100, unique=True)

    class Meta:
        verbose_name = 'Categoría de egreso'
        verbose_name_plural = 'Categorías de egresos'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Egreso(models.Model):
    """
    Registro de egreso o gasto de El Choli.

    Ejemplos: Compra de hielo, verduras, cambio, pago domiciliario, etc.
    """
    METODOS_PAGO = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
    ]

    caja = models.ForeignKey(
        AperturaCaja, on_delete=models.CASCADE,
        related_name='egresos',
        verbose_name='Caja'
    )
    metodo_pago = models.CharField(
        'Método de pago', max_length=20, choices=METODOS_PAGO,
        default='efectivo'
    )
    categoria = models.ForeignKey(
        CategoriaEgreso, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='egresos',
        verbose_name='Categoría'
    )
    valor = models.DecimalField('Valor', max_digits=12, decimal_places=2)
    motivo = models.CharField('Motivo', max_length=200)
    descripcion = models.TextField('Descripción', blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name='Usuario'
    )
    soporte = models.FileField(
        'Archivo de soporte', upload_to='egresos/',
        blank=True, null=True
    )
    created_at = models.DateTimeField('Fecha', auto_now_add=True)

    class Meta:
        verbose_name = 'Egreso'
        verbose_name_plural = 'Egresos'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.motivo} - ${self.valor}'
