"""
Servicios de la aplicación caja.

Contiene la lógica de negocio para gestión de caja.
"""
from datetime import date, datetime
from django.db.models import Sum
from .models import AperturaCaja, Egreso
from apps.ventas.models import Pago


def obtener_resumen_caja(caja):
    """
    Genera el resumen completo de una caja.

    Retorna un diccionario con todas las métricas.
    """
    ventas_efectivo = Pago.objects.filter(
        metodo='efectivo',
        created_at__gte=caja.fecha_apertura,
        created_at__lte=caja.fecha_cierre or datetime.now(),
    ).aggregate(total=Sum('monto'))['total'] or 0

    ventas_transferencia = Pago.objects.filter(
        metodo='transferencia',
        created_at__gte=caja.fecha_apertura,
        created_at__lte=caja.fecha_cierre or datetime.now(),
    ).aggregate(total=Sum('monto'))['total'] or 0

    egresos = caja.egresos.aggregate(total=Sum('valor'))['total'] or 0

    total_ventas = ventas_efectivo + ventas_transferencia
    dinero_esperado = caja.monto_inicial + ventas_efectivo - egresos
    diferencia = total_ventas - egresos

    return {
        'monto_inicial': caja.monto_inicial,
        'ventas_efectivo': ventas_efectivo,
        'ventas_transferencia': ventas_transferencia,
        'total_ventas': total_ventas,
        'egresos': egresos,
        'dinero_esperado': dinero_esperado,
        'diferencia': diferencia,
    }


def obtener_caja_del_dia():
    """
    Retorna la caja abierta del día o None.
    """
    return AperturaCaja.objects.filter(
        activa=True,
        fecha_apertura__date=date.today()
    ).first()
