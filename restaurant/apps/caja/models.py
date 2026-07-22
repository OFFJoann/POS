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
    monto_inicial = models.DecimalField(
        'Monto inicial', max_digits=12, decimal_places=2
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
        """Total: inicial + ventas (efectivo+transferencia) - egresos."""
        return self.monto_inicial + self.total_ventas - self.total_egresos

    @property
    def diferencia(self):
        """Diferencia entre lo esperado y lo real."""
        return self.total_ventas - self.total_egresos


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
    Registro de egreso o gasto del restaurante.

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
