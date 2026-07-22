"""
Modelos de la aplicación inventario.

Registra todos los movimientos de inventario:
entradas, salidas y ajustes.
"""
from django.db import models
from django.conf import settings


class MovimientoInventario(models.Model):
    """
    Registro de movimiento de inventario.

    TIPOS:
    - entrada: Ingreso de productos al inventario
    - salida: Salida de productos
    - ajuste: Corrección de inventario
    - venta: Descuento automático por venta
    """
    TIPOS = [
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
        ('ajuste', 'Ajuste'),
        ('venta', 'Venta'),
    ]

    producto = models.ForeignKey(
        'productos.Producto', on_delete=models.PROTECT,
        related_name='movimientos',
        verbose_name='Producto'
    )
    tipo = models.CharField('Tipo', max_length=10, choices=TIPOS, db_index=True)
    cantidad = models.DecimalField('Cantidad', max_digits=12, decimal_places=2)
    stock_anterior = models.DecimalField('Stock anterior', max_digits=12, decimal_places=2)
    stock_nuevo = models.DecimalField('Stock nuevo', max_digits=12, decimal_places=2)
    motivo = models.CharField('Motivo', max_length=255)
    descripcion = models.TextField('Descripción', blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name='Usuario'
    )
    created_at = models.DateTimeField('Creado', auto_now_add=True)

    class Meta:
        verbose_name = 'Movimiento de inventario'
        verbose_name_plural = 'Movimientos de inventario'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tipo']),
            models.Index(fields=['producto', 'created_at']),
        ]

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.producto.nombre} ({self.cantidad})'


class ConsumoInterno(models.Model):
    """
    Registro de consumo interno (hidratación para empleados).

    Productos entregados a empleados que no generan factura
    pero deben descontarse del inventario.
    """
    producto = models.ForeignKey(
        'productos.Producto', on_delete=models.PROTECT,
        related_name='consumos_internos',
        verbose_name='Producto'
    )
    cantidad = models.DecimalField(
        'Cantidad', max_digits=10, decimal_places=2
    )
    empleado = models.ForeignKey(
        'usuarios.Vendedor', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Empleado',
        related_name='consumos_internos'
    )
    motivo = models.CharField('Motivo', max_length=255, blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name='Registrado por'
    )
    created_at = models.DateTimeField('Fecha', auto_now_add=True)

    class Meta:
        verbose_name = 'Consumo interno'
        verbose_name_plural = 'Consumos internos'
        ordering = ['-created_at']

    def __str__(self):
        empleado_str = str(self.empleado) if self.empleado else 'N/A'
        return f'{self.producto.nombre} x {self.cantidad} - {empleado_str}'
