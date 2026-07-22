"""
Vistas de la aplicación productos.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import ProtectedError
from .models import Producto, Categoria, UnidadMedida
from .forms import ProductoForm, CategoriaForm, UnidadMedidaForm
from .services import buscar_productos_por_termino
from apps.usuarios.decorators import admin_required


@login_required
@admin_required
def lista_productos(request):
    """Lista todos los productos."""
    productos = Producto.objects.select_related('categoria', 'unidad').all()
    return render(request, 'productos/lista_productos.html', {
        'productos': productos,
    })


@login_required
@admin_required
def crear_producto(request):
    """Crea un nuevo producto."""
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Producto creado correctamente.')
            return redirect('lista_productos')
    else:
        form = ProductoForm()
    return render(request, 'productos/form_producto.html', {
        'form': form, 'accion': 'Crear'
    })


@login_required
@admin_required
def editar_producto(request, pk):
    """Edita un producto existente."""
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Producto actualizado correctamente.')
            return redirect('lista_productos')
    else:
        form = ProductoForm(instance=producto)
    return render(request, 'productos/form_producto.html', {
        'form': form, 'accion': 'Editar', 'producto': producto
    })


@login_required
@admin_required
def eliminar_producto(request, pk):
    """Elimina un producto. Si hay registros que lo protegen, muestra dónde."""
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        try:
            nombre = producto.nombre
            producto.delete()
            messages.success(request, f'Producto "{nombre}" eliminado correctamente.')
            return redirect('lista_productos')
        except ProtectedError as e:
            related = {}
            for obj in e.protected_objects:
                key = obj._meta.model_name
                if key not in related:
                    related[key] = {
                        'verbose_name': obj._meta.verbose_name_plural.capitalize(),
                        'count': 0,
                        'objects': [],
                        'app_label': obj._meta.app_label,
                    }
                related[key]['count'] += 1
                if len(related[key]['objects']) < 20:
                    related[key]['objects'].append(obj)
            return render(request, 'productos/error_eliminar_producto.html', {
                'producto': producto,
                'related': related.values(),
            })
    return render(request, 'productos/confirmar_eliminar.html', {
        'producto': producto
    })


@login_required
def lista_precios(request):
    """
    Página de consulta rápida de precios.
    Accesible para todos los usuarios.
    """
    categorias = Categoria.objects.filter(activo=True)
    productos = Producto.objects.filter(estado='activo').select_related('categoria')
    return render(request, 'productos/lista_precios.html', {
        'productos': productos,
        'categorias': categorias,
    })


@login_required
def buscar_productos(request):
    """
    Búsqueda instantánea de productos.
    Retorna JSON para consumo con JavaScript.
    """
    termino = request.GET.get('q', '')
    if termino:
        productos = buscar_productos_por_termino(termino)
    else:
        productos = Producto.objects.filter(estado='activo')[:20]

    data = [{
        'id': p.id,
        'codigo': p.codigo,
        'nombre': p.nombre,
        'precio_venta': float(p.precio_venta),
        'categoria': p.categoria.nombre,
        'stock_actual': float(p.stock_actual),
        'unidad': p.unidad.abreviatura,
    } for p in productos]

    return JsonResponse({'productos': data})


@login_required
@admin_required
def lista_categorias(request):
    """Lista todas las categorías."""
    categorias = Categoria.objects.all()
    return render(request, 'productos/lista_categorias.html', {
        'categorias': categorias,
    })


@login_required
@admin_required
def crear_categoria(request):
    """Crea una nueva categoría."""
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría creada correctamente.')
            return redirect('lista_categorias')
    else:
        form = CategoriaForm()
    return render(request, 'productos/form_categoria.html', {
        'form': form
    })


@login_required
@admin_required
def lista_unidades(request):
    """Lista todas las unidades de medida."""
    unidades = UnidadMedida.objects.all()
    return render(request, 'productos/lista_unidades.html', {
        'unidades': unidades,
    })


@login_required
@admin_required
def crear_unidad(request):
    """Crea una nueva unidad de medida."""
    if request.method == 'POST':
        form = UnidadMedidaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Unidad de medida creada correctamente.')
            return redirect('lista_unidades')
    else:
        form = UnidadMedidaForm()
    return render(request, 'productos/form_unidad.html', {
        'form': form, 'accion': 'Crear'
    })


@login_required
@admin_required
def editar_unidad(request, pk):
    """Edita una unidad de medida existente."""
    unidad = get_object_or_404(UnidadMedida, pk=pk)
    if request.method == 'POST':
        form = UnidadMedidaForm(request.POST, instance=unidad)
        if form.is_valid():
            form.save()
            messages.success(request, 'Unidad de medida actualizada correctamente.')
            return redirect('lista_unidades')
    else:
        form = UnidadMedidaForm(instance=unidad)
    return render(request, 'productos/form_unidad.html', {
        'form': form, 'accion': 'Editar', 'unidad': unidad
    })
