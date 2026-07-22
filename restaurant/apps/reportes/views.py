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
from apps.usuarios.decorators import admin_required
from apps.ventas.models import Factura, Pago
from apps.productos.models import Producto
from apps.usuarios.models import Vendedor
from apps.mesas.models import DetallePedido


@login_required
@admin_required
def dashboard_reportes(request):
    """Dashboard principal de reportes."""
    datos = obtener_datos_dashboard()
    return render(request, 'reportes/dashboard_reportes.html', datos)


@login_required
@admin_required
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

    return render(request, 'reportes/reporte_ventas.html', {
        'facturas': facturas,
        'totales': totales,
        'vendedores': vendedores,
    })


@login_required
@admin_required
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
@admin_required
def exportar_ventas_pdf(request):
    """Exporta ventas filtradas a PDF."""
    facturas = Factura.objects.select_related('mesa', 'mesero').all()

    fecha_desde = request.GET.get('desde')
    fecha_hasta = request.GET.get('hasta')
    if fecha_desde:
        facturas = facturas.filter(created_at__gte=fecha_desde)
    if fecha_hasta:
        facturas = facturas.filter(created_at__lte=fecha_hasta)

    from apps.ventas.services import render_pdf
    response = render_pdf('reportes/reporte_ventas_pdf.html', {
        'facturas': facturas,
        'fecha_generacion': datetime.now(),
    })
    response['Content-Disposition'] = 'attachment; filename=reporte_ventas.pdf'
    return response


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
@admin_required
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
@admin_required
def exportar_productos_excel(request):
    """Exporta productos a Excel."""
    productos = Producto.objects.select_related('categoria').all()
    return exportar_excel_productos(productos)


@login_required
@admin_required
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
@admin_required
def datos_dashboard_api(request):
    """API que retorna datos del dashboard en JSON."""
    datos = obtener_datos_dashboard()

    for key, value in datos.items():
        if isinstance(value, Decimal):
            datos[key] = float(value)
        elif isinstance(value, (list, models.QuerySet)):
            datos[key] = list(value)

    return JsonResponse(datos)
