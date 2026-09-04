"""
Vistas de la aplicación ventas.

Incluye listado de facturas, detalle y exportación PDF.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from io import BytesIO
from datetime import date
from .models import Factura
from apps.usuarios.decorators import permiso_required


@login_required
@permiso_required('ver_facturas')
def lista_facturas(request):
    """
    Lista las facturas generadas.

    Administradores y quienes tienen 'ver_facturas' ven todas las facturas;
    los demás vendedores solo ven las suyas.
    """
    v = getattr(request.user, 'vendedor', None)
    if request.user.is_staff or (v and v.puede('ver_facturas')):
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


def _puede_ver_factura(user, factura=None):
    """
    Reglas para ver una factura:
    - Administrador: siempre, cualquier factura.
    - Permiso 'ver_facturas': ve cualquier factura.
    - Solo 'facturar' (sin 'ver_facturas'): solo sus propias facturas.
    - Sin permisos: ninguna.
    """
    if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
        return True
    v = getattr(user, 'vendedor', None)
    if not v:
        return False
    if v.puede('ver_facturas'):
        return True
    if v.puede('facturar'):
        return factura is None or factura.mesero_id == v.id
    return False


@login_required
def ver_factura(request, factura_id):
    """
    Muestra el detalle de una factura.
    """
    factura = get_object_or_404(
        Factura.objects.select_related('mesa', 'mesero', 'pedido'),
        pk=factura_id
    )
    if not _puede_ver_factura(request.user, factura):
        messages.error(request, 'No tienes permiso para ver esta factura.')
        return redirect('vista_mesas')
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
    if not _puede_ver_factura(request.user, factura):
        messages.error(request, 'No tienes permiso para ver esta factura.')
        return redirect('vista_mesas')

    from .services import generar_factura_pdf
    return generar_factura_pdf(factura)


@login_required
@permiso_required('ver_facturas')
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


@login_required
def mis_comisiones(request):
    """
    Muestra las comisiones del usuario actual en la caja activa.
    """
    from apps.caja.models import AperturaCaja
    from apps.ventas.services import comisiones_por_vendedor

    vendedor = getattr(request.user, 'vendedor', None)
    if not vendedor:
        messages.error(request, 'No tienes perfil de vendedor.')
        return redirect('vista_mesas')

    caja = AperturaCaja.objects.filter(activa=True).first()
    comisiones = []
    total_comisiones = 0
    mi_comision = None

    if caja:
        comisiones = comisiones_por_vendedor(
            caja.fecha_apertura, caja._fecha_fin
        )
        total_comisiones = sum((c['total'] or 0) for c in comisiones)
        for c in comisiones:
            if c['id'] == vendedor.id:
                mi_comision = c
                break

    return render(request, 'ventas/mis_comisiones.html', {
        'mi_comision': mi_comision,
        'total_comisiones': total_comisiones,
        'caja': caja,
    })
