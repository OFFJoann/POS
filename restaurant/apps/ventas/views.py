"""
Vistas de la aplicación ventas.

Incluye listado de facturas, detalle y exportación PDF.
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from io import BytesIO
from datetime import date
from .models import Factura


@login_required
def lista_facturas(request):
    """
    Lista todas las facturas generadas.

    Los administradores ven todas, los vendedores solo las suyas.
    """
    if request.user.is_staff:
        facturas = Factura.objects.select_related('mesa', 'mesero').all()
    else:
        facturas = Factura.objects.filter(
            mesero=request.user.vendedor
        ).select_related('mesa', 'mesero')

    # Filtros
    fecha_desde = request.GET.get('desde')
    fecha_hasta = request.GET.get('hasta')
    metodo = request.GET.get('metodo')

    if fecha_desde:
        facturas = facturas.filter(created_at__gte=fecha_desde)
    if fecha_hasta:
        facturas = facturas.filter(created_at__lte=fecha_hasta)
    if metodo:
        facturas = facturas.filter(metodo_pago=metodo)

    return render(request, 'ventas/lista_facturas.html', {
        'facturas': facturas,
    })


@login_required
def ver_factura(request, factura_id):
    """
    Muestra el detalle de una factura.
    """
    factura = get_object_or_404(
        Factura.objects.select_related('mesa', 'mesero', 'pedido'),
        pk=factura_id
    )
    detalles = factura.pedido.detalles.select_related('producto').all()
    pagos = factura.pagos.all()

    return render(request, 'ventas/ver_factura.html', {
        'factura': factura,
        'detalles': detalles,
        'pagos': pagos,
    })


@login_required
def factura_pdf(request, factura_id):
    """
    Genera y descarga el PDF de una factura.
    """
    factura = get_object_or_404(Factura, pk=factura_id)
    detalles = factura.pedido.detalles.select_related('producto').all()

    from .services import render_pdf
    response = render_pdf('ventas/factura_pdf.html', {
        'factura': factura,
        'detalles': detalles,
    })
    response['Content-Disposition'] = f'filename=factura_{factura.numero}.pdf'
    return response


@login_required
def buscar_facturas(request):
    """
    Búsqueda instantánea de facturas.
    """
    termino = request.GET.get('q', '')

    facturas = Factura.objects.select_related('mesa', 'mesero')
    if not request.user.is_staff:
        facturas = facturas.filter(mesero=request.user.vendedor)

    if termino:
        facturas = facturas.filter(
            Q(numero__icontains=termino) |
            Q(mesa__numero__icontains=termino) |
            Q(mesero__nombre__icontains=termino)
        )

    data = [{
        'id': f.id,
        'numero': f.numero,
        'mesa': f.mesa.numero,
        'mesero': str(f.mesero),
        'total': float(f.total),
        'metodo_pago': f.get_metodo_pago_display(),
        'fecha': f.created_at.strftime('%d/%m/%Y %H:%M'),
        'url': f'/ventas/factura/{f.id}/',
    } for f in facturas[:50]]

    return JsonResponse({'facturas': data})
