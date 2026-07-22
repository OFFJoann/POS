"""
Vistas de la aplicación inventario.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from .models import MovimientoInventario, ConsumoInterno
from .forms import MovimientoInventarioForm, ConsumoInternoForm
from .services import registrar_movimiento as servicio_registrar_movimiento
from apps.usuarios.decorators import admin_required
from apps.productos.models import Producto


@login_required
@admin_required
def lista_inventario(request):
    """
    Vista principal de inventario.

    Muestra todos los productos con su stock actual.
    """
    productos = Producto.objects.select_related('categoria', 'unidad').all()
    return render(request, 'inventario/lista_inventario.html', {
        'productos': productos,
    })


@login_required
@admin_required
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
@admin_required
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
@admin_required
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
