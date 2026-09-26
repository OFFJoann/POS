"""
Vistas de la aplicación inventario.
"""
from datetime import time
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from .models import MovimientoInventario, ConsumoInterno
from .forms import MovimientoInventarioForm, ConsumoInternoForm
from .services import registrar_movimiento as servicio_registrar_movimiento
from apps.usuarios.decorators import admin_required, permiso_required
from apps.productos.models import Producto, Categoria
from apps.caja.models import AperturaCaja


@login_required
@permiso_required('inventario')
def lista_inventario(request):
    """
    Vista principal de inventario.

    Muestra los productos con su stock actual, agrupados por categoría.
    """
    categorias = Categoria.objects.all().order_by('orden', 'nombre')
    productos_por_categoria = {}
    for cat in categorias:
        prods = Producto.objects.filter(
            categoria=cat, es_combo=False
        ).select_related('unidad', 'categoria')
        if prods.exists():
            productos_por_categoria[cat] = prods
    return render(request, 'inventario/lista_inventario.html', {
        'productos_por_categoria': productos_por_categoria,
    })


@login_required
@permiso_required('inventario')
def registrar_movimiento(request):
    """
    Registra un movimiento de inventario (entrada, salida, ajuste).
    """
    if request.method == 'POST':
        form = MovimientoInventarioForm(request.POST)
        if form.is_valid():
            producto = form.cleaned_data['producto']
            tipo = form.cleaned_data['tipo']
            cantidad = form.cleaned_data['cantidad']
            motivo = form.cleaned_data['motivo']
            descripcion = form.cleaned_data['descripcion']

            servicio_registrar_movimiento(
                producto=producto,
                tipo=tipo,
                cantidad=cantidad,
                motivo=motivo,
                descripcion=descripcion,
                usuario=request.user,
            )
            messages.success(request, 'Movimiento registrado correctamente.')
            return redirect('lista_inventario')
    else:
        form = MovimientoInventarioForm()

    return render(request, 'inventario/form_movimiento.html', {
        'form': form,
    })


@login_required
@permiso_required('inventario')
def historial_inventario(request):
    """
    Historial completo de movimientos de inventario.
    """
    movimientos = MovimientoInventario.objects.select_related(
        'producto', 'usuario'
    ).all()

    # Filtros
    tipo = request.GET.get('tipo')
    producto_id = request.GET.get('producto')
    if tipo:
        movimientos = movimientos.filter(tipo=tipo)
    if producto_id:
        movimientos = movimientos.filter(producto_id=producto_id)

    productos = Producto.objects.filter(estado='activo')

    return render(request, 'inventario/historial_inventario.html', {
        'movimientos': movimientos,
        'productos': productos,
        'filtro_tipo': tipo,
        'filtro_producto': int(producto_id) if producto_id else None,
    })


@login_required
def buscar_inventario(request):
    """
    Búsqueda instantánea de productos en inventario.
    """
    termino = request.GET.get('q', '')
    if termino:
        productos = Producto.objects.filter(
            Q(codigo__icontains=termino) |
            Q(nombre__icontains=termino)
        ).select_related('categoria', 'unidad')
    else:
        productos = Producto.objects.all().select_related('categoria', 'unidad')

    data = [{
        'id': p.id,
        'codigo': p.codigo,
        'nombre': p.nombre,
        'categoria': p.categoria.nombre,
        'stock_actual': float(p.stock_actual),
        'stock_minimo': float(p.stock_minimo),
        'unidad': p.unidad.abreviatura,
        'estado': p.estado,
    } for p in productos]

    return JsonResponse({'productos': data})


@login_required
@permiso_required('inventario')
def registrar_consumo_interno(request):
    """
    Registra consumo interno (hidratación para empleados).
    Descarta del inventario sin generar factura.
    """
    if request.method == 'POST':
        form = ConsumoInternoForm(request.POST)
        if form.is_valid():
            consumo = form.save(commit=False)
            consumo.usuario = request.user
            consumo.save()

            from .services import registrar_movimiento
            empleado = str(consumo.empleado) if consumo.empleado else 'N/A'
            registrar_movimiento(
                producto=consumo.producto,
                tipo='salida',
                cantidad=consumo.cantidad,
                motivo=f'Consumo interno: {empleado}',
                usuario=request.user,
            )
            messages.success(request, 'Consumo interno registrado y descontado del inventario.')
            return redirect('lista_inventario')
    else:
        form = ConsumoInternoForm()

    return render(request, 'inventario/form_consumo_interno.html', {
        'form': form,
    })


@login_required
@permiso_required('inventario')
def historial_snapshots(request):
    """
    Muestra el inventario registrado en cada apertura de caja.

    Cada vez que se abre caja se guarda un snapshot del stock. Por defecto
    se muestran las 5 aperturas más recientes; con `desde`/`hasta`
    (YYYY-MM-DD) se filtra por fecha de apertura y con `q` por producto.
    """
    def _parsear_fecha(valor):
        try:
            return timezone.datetime.strptime(valor, '%Y-%m-%d').date()
        except (TypeError, ValueError):
            return None

    desde = _parsear_fecha(request.GET.get('desde'))
    hasta = _parsear_fecha(request.GET.get('hasta'))
    termino = request.GET.get('q', '')

    aperturas = (
        AperturaCaja.objects
        .filter(snapshots_inventario__momento='apertura')
        .distinct()
        .order_by('-fecha_apertura')
    )

    if desde and hasta:
        if desde > hasta:
            desde, hasta = hasta, desde
        desde_dt = timezone.make_aware(timezone.datetime.combine(desde, time.min))
        hasta_dt = timezone.make_aware(timezone.datetime.combine(hasta, time.max))
        aperturas = aperturas.filter(
            fecha_apertura__gte=desde_dt,
            fecha_apertura__lte=hasta_dt,
        )
    else:
        aperturas = aperturas[:5]

    aperturas = list(aperturas)

    datos = []
    for ca in aperturas:
        apertura_snaps = (
            ca.snapshots_inventario
            .filter(momento='apertura')
            .select_related('producto', 'producto__unidad')
        )
        cierre_snaps = {
            s.producto_id: s.cantidad
            for s in ca.snapshots_inventario.filter(momento='cierre')
        }
        filas = []
        for s in apertura_snaps:
            producto = s.producto
            if termino and termino.lower() not in producto.nombre.lower():
                continue
            final = cierre_snaps.get(s.producto_id)
            filas.append({
                'producto': producto,
                'inicial': s.cantidad,
                'final': final,
                'consumido': (s.cantidad - final) if final is not None else None,
            })
        filas.sort(key=lambda f: f['producto'].nombre)
        datos.append({
            'caja': ca,
            'filas': filas,
        })

    return render(request, 'inventario/snapshots_inventario.html', {
        'datos': datos,
        'desde': desde,
        'hasta': hasta,
        'termino': termino,
    })
