"""
Servicios de la aplicación productos.

Contiene la lógica de negocio para gestión de productos.
"""
from django.db.models import Q, F
from .models import Producto, Categoria


def buscar_productos_por_termino(termino):
    """
    Busca productos por código o nombre.
    Retorna resultados que coincidan parcialmente.
    """
    return Producto.objects.filter(
        Q(codigo__icontains=termino) |
        Q(nombre__icontains=termino),
        estado='activo'
    ).select_related('categoria', 'unidad')[:20]


def obtener_productos_stock_bajo():
    """
    Retorna productos cuyo stock actual está por debajo
    o igual al stock mínimo.
    """
    return Producto.objects.filter(
        stock_actual__lte=F('stock_minimo'),
        estado='activo'
    ).select_related('categoria')


def obtener_categorias_activas():
    """Retorna categorías activas."""
    return Categoria.objects.filter(activo=True)
