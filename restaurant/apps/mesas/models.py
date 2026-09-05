"""
Modelos de la aplicación mesas.

Gestiona las mesas de El Choli y sus pedidos activos.
"""
from django.db import models
from django.conf import settings
from django.db.models import Sum


class Mesa(models.Model):
    """
    Mesa de El Choli.

    Cada mesa tiene un estado visual que se refleja con colores.
    """
    ESTADOS = [
        ('libre', '🟢 Libre'),
        ('activo', '🟡 Pedido activo'),
        ('parcial', '🟠 Pago parcial'),
        ('pagada', '🔵 Pagada'),
        ('cerrada', '🔴 Cerrada'),
    ]

    numero = models.PositiveIntegerField(
        'Número de mesa', unique=True,
        db_index=True
    )
    estado = models.CharField(
        'Estado', max_length=10, choices=ESTADOS,
        default='libre', db_index=True
    )
    activa = models.BooleanField('Activa', default=True)

    class Meta:
        verbose_name = 'Mesa'
        verbose_name_plural = 'Mesas'
        ordering = ['numero']

    def __str__(self):
        return f'Mesa {self.numero}'


class SolicitudPedido(models.Model):
    """
    Solicitud de un pedido enviada a caja ("Solicitar en caja").

    Agrupa los detalles de un pedido que un mesero envía al receptor de
    pedidos. Permanece pendiente hasta que el receptor la atiende.
    """
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('atendida', 'Atendida'),
    ]

    pedido = models.ForeignKey(
        'Pedido', on_delete=models.CASCADE,
        related_name='solicitudes', verbose_name='Pedido'
    )
    mesa = models.ForeignKey(
        Mesa, on_delete=models.CASCADE,
        related_name='solicitudes', verbose_name='Mesa'
    )
    solicitante = models.ForeignKey(
        'usuarios.Vendedor', on_delete=models.SET_NULL, null=True,
        related_name='solicitudes_enviadas', verbose_name='Solicitante'
    )
    estado = models.CharField(
        'Estado', max_length=10, choices=ESTADOS, default='pendiente'
    )
    created_at = models.DateTimeField('Creado', auto_now_add=True)

    class Meta:
        verbose_name = 'Solicitud de pedido'
        verbose_name_plural = 'Solicitudes de pedido'
        ordering = ['-created_at']

    def __str__(self):
        return f'Solicitud #{self.id} - Mesa {self.mesa.numero}'


class Pedido(models.Model):
    """
    Pedido realizado en una mesa.

    Contiene los productos, cantidades y totales.
    """
    mesa = models.ForeignKey(
        Mesa, on_delete=models.CASCADE,
        related_name='pedidos',
        verbose_name='Mesa'
    )
    mesero = models.ForeignKey(
        'usuarios.Vendedor', on_delete=models.PROTECT,
        related_name='pedidos',
        verbose_name='Mesero'
    )
    productos = models.ManyToManyField(
        'productos.Producto',
        through='DetallePedido',
        related_name='pedidos',
        verbose_name='Productos'
    )
    observaciones = models.TextField('Observaciones', blank=True)
    subtotal = models.DecimalField(
        'Subtotal', max_digits=12, decimal_places=2,
        default=0
    )
    descuento = models.DecimalField(
        'Descuento', max_digits=12, decimal_places=2,
        default=0
    )
    total = models.DecimalField(
        'Total', max_digits=12, decimal_places=2, default=0
    )
    saldo_pendiente = models.DecimalField(
        'Saldo pendiente', max_digits=12, decimal_places=2,
        default=0
    )
    estado = models.CharField(
        'Estado', max_length=10,
        choices=[('activo', 'Activo'), ('pagado', 'Pagado'),
                 ('parcial', 'Pago Parcial'), ('cerrado', 'Cerrado')],
        default='activo', db_index=True
    )
    fecha_apertura = models.DateTimeField('Fecha apertura', auto_now_add=True)
    fecha_cierre = models.DateTimeField('Fecha cierre', null=True, blank=True)
    sesion_inicio = models.DateTimeField(
        'Inicio de sesión', null=True, blank=True,
        help_text='Última vez que el mesero entró a la mesa; '
                  'Solicitar en caja solo envía productos desde esta fecha.'
    )
    created_at = models.DateTimeField('Creado', auto_now_add=True)
    updated_at = models.DateTimeField('Actualizado', auto_now=True)

    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-fecha_apertura']
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['mesa', 'estado']),
            models.Index(fields=['mesero']),
        ]

    def __str__(self):
        return f'Pedido #{self.id} - Mesa {self.mesa.numero}'

    def calcular_totales(self):
        """Recalcula subtotal, descuento, total y saldo pendiente del pedido."""
        detalles = self.detalles.all()
        self.subtotal = sum(d.subtotal for d in detalles)
        self.total = self.subtotal - self.descuento
        if self.total < 0:
            self.total = 0
        self.saldo_pendiente = self.falta_por_cobrar
        self.save(update_fields=['subtotal', 'total', 'descuento', 'saldo_pendiente'])

    @property
    def falta_por_cobrar(self):
        """
        Monto real que falta por cobrar de este pedido.

        Se calcula como el total menos lo ya pagado, sin depender del campo
        ``saldo_pendiente`` que puede quedar desactualizado si se modifican
        productos, cantidades o precios después de un pago parcial.
        """
        pagado = self.pagos.aggregate(total=Sum('monto'))['total'] or 0
        return max(self.total - pagado, 0)


class DetallePedido(models.Model):
    """
    Producto individual dentro de un pedido.
    """
    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE,
        related_name='detalles',
        verbose_name='Pedido'
    )
    producto = models.ForeignKey(
        'productos.Producto', on_delete=models.PROTECT,
        related_name='detalles_pedido',
        verbose_name='Producto'
    )
    cantidad = models.DecimalField(
        'Cantidad', max_digits=10, decimal_places=2, default=1
    )
    precio_unitario = models.DecimalField(
        'Precio unitario', max_digits=12, decimal_places=2
    )
    subtotal = models.DecimalField(
        'Subtotal', max_digits=12, decimal_places=2
    )
    comision = models.DecimalField(
        'Comisión', max_digits=12, decimal_places=2, default=0
    )
    es_cortesia = models.BooleanField('Cortesía', default=False)
    observaciones = models.CharField(
        'Observaciones', max_length=255, blank=True
    )
    solicitud = models.ForeignKey(
        'SolicitudPedido', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='detalles', verbose_name='Solicitud enviada'
    )
    created_at = models.DateTimeField('Creado', auto_now_add=True)

    class Meta:
        verbose_name = 'Detalle del pedido'
        verbose_name_plural = 'Detalles del pedido'
        indexes = [
            models.Index(fields=['pedido', 'producto']),
        ]

    def __str__(self):
        return f'{self.producto.nombre} x {self.cantidad}'

    def save(self, *args, **kwargs):
        """Calcula subtotal y comisión automáticamente antes de guardar."""
        self.subtotal = self.cantidad * self.precio_unitario
        if self.es_cortesia:
            self.comision = 0
        else:
            self.comision = self.cantidad * self.producto.comision
        super().save(*args, **kwargs)
