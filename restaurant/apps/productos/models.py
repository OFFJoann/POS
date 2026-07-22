"""
Modelos de la aplicación productos.

Define categorías y productos del restaurante.
"""
from django.db import models


class Categoria(models.Model):
    """
    Categoría de productos.
    Ejemplo: Bebidas, Comidas, Postres, etc.
    """
    nombre = models.CharField('Nombre', max_length=100, unique=True)
    descripcion = models.TextField('Descripción', blank=True)
    activo = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class UnidadMedida(models.Model):
    """
    Unidad de medida para productos.
    Ejemplo: Unidad, Litro, Kilo, Libra, etc.
    """
    nombre = models.CharField('Nombre', max_length=50, unique=True)
    abreviatura = models.CharField('Abreviatura', max_length=10)

    class Meta:
        verbose_name = 'Unidad de medida'
        verbose_name_plural = 'Unidades de medida'

    def __str__(self):
        return f'{self.nombre} ({self.abreviatura})'


class Producto(models.Model):
    """
    Producto del menú del restaurante.

    Cada producto tiene su precio, costo y control de stock.
    """
    ESTADOS = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('agotado', 'Agotado'),
    ]

    codigo = models.CharField(
        'Código', max_length=50, unique=True,
        db_index=True
    )
    nombre = models.CharField('Nombre', max_length=200)
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT,
        related_name='productos',
        verbose_name='Categoría'
    )
    unidad = models.ForeignKey(
        UnidadMedida, on_delete=models.PROTECT,
        related_name='productos',
        verbose_name='Unidad de medida'
    )
    precio_venta = models.IntegerField('Precio de venta')
    costo = models.IntegerField('Costo', default=0)
    stock_actual = models.IntegerField('Stock actual', default=0)
    stock_minimo = models.IntegerField('Stock mínimo', default=0)
    imagen = models.ImageField(
        'Imagen', upload_to='productos/', blank=True, null=True
    )
    estado = models.CharField(
        'Estado', max_length=10, choices=ESTADOS,
        default='activo', db_index=True
    )
    created_at = models.DateTimeField('Creado', auto_now_add=True)
    updated_at = models.DateTimeField('Actualizado', auto_now=True)

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['estado']),
            models.Index(fields=['categoria']),
        ]

    def __str__(self):
        return f'{self.codigo} - {self.nombre}'

    @property
    def stock_bajo(self):
        """Indica si el stock está por debajo del mínimo."""
        return self.stock_actual <= self.stock_minimo
