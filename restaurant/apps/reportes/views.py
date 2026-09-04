"""
Vistas de la aplicación reportes.

Incluye dashboard, reportes detallados y exportación.
"""
from decimal import Decimal
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db import models
from django.db.models import Sum, Count, Q, F
from datetime import date, datetime
from .services import (
    obtener_datos_dashboard,
    exportar_ventas_excel as exportar_excel_ventas,
    exportar_productos_excel as exportar_excel_productos,
)
from apps.usuarios.decorators import admin_required, permiso_required
from apps.ventas.models import Factura, Pago
from apps.productos.models import Producto
from apps.usuarios.models import Vendedor
from apps.mesas.models import DetallePedido


@login_required
@permiso_required('reportes')
def dashboard_reportes(request):
    """Dashboard principal de reportes."""
    datos = obtener_datos_dashboard()
    return render(request, 'reportes/dashboard_reportes.html', datos)


@login_required
@permiso_required('reportes')
def reporte_ventas(request):
    """Reporte detallado de ventas con filtros."""
    facturas = Factura.objects.select_related('mesa', 'mesero').all()

    fecha_desde = request.GET.get('desde')
    fecha_hasta = request.GET.get('hasta')
    mesero_id = request.GET.get('mesero')
    metodo = request.GET.get('metodo')
    mesa_numero = request.GET.get('mesa')

    if fecha_desde:
        facturas = facturas.filter(created_at__gte=fecha_desde)
    if fecha_hasta:
        facturas = facturas.filter(created_at__lte=fecha_hasta)
    if mesero_id:
        facturas = facturas.filter(mesero_id=mesero_id)
    if metodo:
        facturas = facturas.filter(metodo_pago=metodo)
    if mesa_numero:
        facturas = facturas.filter(mesa__numero=mesa_numero)

    totales = facturas.aggregate(
        total_ventas=Sum('total'),
        descuentos=Sum('descuento'),
        efectivo=Sum('total', filter=Q(metodo_pago='efectivo')),
        transferencia=Sum('total', filter=Q(metodo_pago='transferencia')),
    )

    vendedores = Vendedor.objects.filter(activo=True)

    from apps.ventas.services import comisiones_por_vendedor
    comisiones = comisiones_por_vendedor(
        desde=fecha_desde,
        hasta=fecha_hasta,
        mesero=int(mesero_id) if mesero_id else None,
    )
    total_comisiones = sum((c['total'] or 0) for c in comisiones)

    return render(request, 'reportes/reporte_ventas.html', {
        'facturas': facturas,
        'totales': totales,
        'vendedores': vendedores,
        'comisiones': comisiones,
        'total_comisiones': total_comisiones,
    })


@login_required
@permiso_required('reportes')
def exportar_ventas_excel(request):
    """Exporta ventas filtradas a Excel."""
    facturas = Factura.objects.select_related('mesa', 'mesero').all()

    fecha_desde = request.GET.get('desde')
    fecha_hasta = request.GET.get('hasta')
    if fecha_desde:
        facturas = facturas.filter(created_at__gte=fecha_desde)
    if fecha_hasta:
        facturas = facturas.filter(created_at__lte=fecha_hasta)

    return exportar_excel_ventas(facturas)


@login_required
@permiso_required('reportes')
def exportar_ventas_pdf(request):
    """Exporta ventas filtradas a PDF."""
    facturas = Factura.objects.select_related('mesa', 'mesero').all()

    fecha_desde = request.GET.get('desde')
    fecha_hasta = request.GET.get('hasta')
    if fecha_desde:
        facturas = facturas.filter(created_at__gte=fecha_desde)
    if fecha_hasta:
        facturas = facturas.filter(created_at__lte=fecha_hasta)

    from apps.ventas.services import generar_reporte_ventas_pdf
    return generar_reporte_ventas_pdf(facturas, datetime.now())


def _agregar_ganancia(queryset):
    """Agrega ganancia_unitaria y ganancia_total a cada item del queryset."""
    items = list(queryset)
    ganancia_total_general = 0
    for item in items:
        costo = item.get('producto__costo') or 0
        precio = item.get('producto__precio_venta') or 0
        vendido = item.get('total_vendido') or 0
        item['ganancia_unitaria'] = precio - costo
        item['ganancia_total'] = item['ganancia_unitaria'] * vendido
        ganancia_total_general += item['ganancia_total']
    return items, ganancia_total_general


@login_required
@permiso_required('reportes')
def reporte_productos(request):
    """Reporte de productos: más/menos vendidos, ganancia, cortesías."""
    base = DetallePedido.objects.exclude(es_cortesia=True).values(
        'producto__nombre', 'producto__codigo',
        'producto__costo', 'producto__precio_venta'
    ).annotate(total_vendido=Sum('cantidad'))

    mas_vendidos, _ = _agregar_ganancia(base.order_by('-total_vendido')[:20])
    menos_vendidos, _ = _agregar_ganancia(base.order_by('total_vendido')[:20])
    ventas_con_costo, ganancia_total_general = _agregar_ganancia(
        base.exclude(producto__costo=0)
    )

    cortesias_hoy = DetallePedido.objects.filter(
        es_cortesia=True,
        created_at__date=date.today()
    ).select_related('producto', 'pedido__mesa')

    stock_bajo = Producto.objects.filter(
        stock_actual__lte=F('stock_minimo')
    ).select_related('categoria')

    total_invertido = Producto.objects.aggregate(
        total=Sum(F('costo') * F('stock_actual'))
    )['total'] or 0

    ganancia_potencial = Producto.objects.aggregate(
        total=Sum((F('precio_venta') - F('costo')) * F('stock_actual'))
    )['total'] or 0

    return render(request, 'reportes/reporte_productos.html', {
        'mas_vendidos': mas_vendidos,
        'menos_vendidos': menos_vendidos,
        'cortesias_hoy': cortesias_hoy,
        'stock_bajo': stock_bajo,
        'ganancia_total_general': ganancia_total_general,
        'total_invertido': total_invertido,
        'ganancia_potencial': ganancia_potencial,
    })


@login_required
@permiso_required('reportes')
def exportar_productos_excel(request):
    """Exporta productos a Excel."""
    productos = Producto.objects.select_related('categoria').all()
    return exportar_excel_productos(productos)


@login_required
@permiso_required('reportes')
def reporte_por_mesero(request, vendedor_id):
    """Reporte de ventas por mesero."""
    vendedor = get_object_or_404(Vendedor, pk=vendedor_id)
    facturas = Factura.objects.filter(mesero=vendedor)

    fecha_desde = request.GET.get('desde')
    fecha_hasta = request.GET.get('hasta')
    if fecha_desde:
        facturas = facturas.filter(created_at__gte=fecha_desde)
    if fecha_hasta:
        facturas = facturas.filter(created_at__lte=fecha_hasta)

    totales = facturas.aggregate(
        total=Sum('total'),
        num_facturas=Count('id'),
    )

    return render(request, 'reportes/reporte_mesero.html', {
        'vendedor': vendedor,
        'facturas': facturas,
        'totales': totales,
    })


@login_required
@permiso_required('reportes')
def datos_dashboard_api(request):
    """API que retorna datos del dashboard en JSON."""
    datos = obtener_datos_dashboard()

    for key, value in datos.items():
        if isinstance(value, Decimal):
            datos[key] = float(value)
        elif isinstance(value, (list, models.QuerySet)):
            datos[key] = list(value)

    return JsonResponse(datos)


@login_required
@permiso_required('reportes')
def metricas_por_hora(request):
    """
    Métrica de ventas promedio por hora.
    Agrega los datos de todos los cierres de caja para mostrar
    a qué horas se vende más el negocio.
    """
    from collections import defaultdict
    from django.db.models import Sum
    from django.db.models.functions import ExtractHour
    from apps.caja.models import CierreCaja

    meses = int(request.GET.get('meses', 3))

    cierres = CierreCaja.objects.select_related('caja').order_by('-fecha_cierre')

    # Acumular ventas por hora de todos los cierres
    ventas_por_hora_total = defaultdict(float)
    conteo_cierres = 0
    cierres_con_datos = []

    for c in cierres[:meses * 30]:
        pagos = Pago.objects.filter(
            created_at__gte=c.caja.fecha_apertura,
            created_at__lte=c.fecha_cierre,
        )
        hora_data = (
            pagos.annotate(hora=ExtractHour('created_at'))
            .values('hora')
            .annotate(total=Sum('monto'))
        )
        if hora_data:
            conteo_cierres += 1
            cierres_con_datos.append({
                'fecha': c.fecha_cierre,
                'total': float(c.total_ventas),
            })
            for item in hora_data:
                ventas_por_hora_total[item['hora']] += float(item['total'])

    # Promediar por hora
    horas_promedio = []
    max_venta = 0
    for h in range(24):
        promedio = ventas_por_hora_total[h] / conteo_cierres if conteo_cierres > 0 else 0
        if promedio > max_venta:
            max_venta = promedio
        horas_promedio.append({
            'hora': str(h),
            'promedio': round(promedio, 0),
            'total_acumulado': round(ventas_por_hora_total[h], 0),
        })

    # Calcular porcentaje para el grafico
    for h in horas_promedio:
        h['porcentaje'] = round((h['promedio'] / max_venta * 100) if max_venta > 0 else 0, 1)

    # Hora pico
    hora_pico = max(horas_promedio, key=lambda x: x['promedio']) if horas_promedio else None

    return render(request, 'reportes/metricas_por_hora.html', {
        'horas': horas_promedio,
        'conteo_cierres': conteo_cierres,
        'hora_pico': hora_pico,
        'meses_seleccionados': meses,
        'cierres_con_datos': cierres_con_datos,
    })
