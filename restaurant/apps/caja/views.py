"""
Vistas de la aplicación caja.

Incluye apertura, cierre de caja y gestión de egresos.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import AperturaCaja, Egreso, CategoriaEgreso
from .forms import AperturaCajaForm, EgresoForm
from apps.usuarios.decorators import admin_required
from apps.mesas.models import Mesa


@login_required
def estado_caja(request):
    """
    Muestra el estado actual de la caja.

    Si hay una caja abierta, muestra sus movimientos.
    """
    caja_activa = AperturaCaja.objects.filter(activa=True).first()
    egresos = Egreso.objects.none()

    if caja_activa:
        egresos = caja_activa.egresos.select_related('usuario', 'categoria').all()

    return render(request, 'caja/estado_caja.html', {
        'caja': caja_activa,
        'egresos': egresos,
    })


@login_required
@admin_required
def abrir_caja(request):
    """
    Abre una nueva caja.

    Solo puede haber una caja abierta a la vez.
    """
    if AperturaCaja.objects.filter(activa=True).exists():
        messages.warning(request, 'Ya hay una caja abierta.')
        return redirect('estado_caja')

    if request.method == 'POST':
        form = AperturaCajaForm(request.POST)
        if form.is_valid():
            caja = form.save(commit=False)
            caja.usuario = request.user
            caja.save()
            messages.success(request, 'Caja abierta correctamente.')
            return redirect('estado_caja')
    else:
        form = AperturaCajaForm()

    return render(request, 'caja/form_apertura.html', {
        'form': form,
    })


@login_required
@admin_required
def cerrar_caja(request):
    """
    Cierra la caja activa y muestra el resumen.

    El resumen incluye: monto inicial, ventas, egresos,
    dinero esperado y diferencia.
    """
    caja = AperturaCaja.objects.filter(activa=True).first()
    if not caja:
        messages.error(request, 'No hay una caja abierta.')
        return redirect('estado_caja')

    # Verificar que no haya mesas sin cobrar
    mesas_pendientes = Mesa.objects.filter(estado__in=['activo', 'parcial'])
    if mesas_pendientes.exists():
        messages.error(
            request,
            f'No se puede cerrar la caja. Hay {mesas_pendientes.count()} mesa(s) con pedidos sin cobrar.'
        )
        return redirect('estado_caja')

    if request.method == 'POST':
        caja.activa = False
        caja.fecha_cierre = timezone.now()
        caja.save()

        messages.success(
            request,
            f'Caja cerrada. Dinero esperado: ${caja.dinero_esperado:0f}'
        )
        return redirect('estado_caja')

    return render(request, 'caja/confirmar_cierre.html', {
        'caja': caja,
    })


@login_required
@admin_required
def lista_egresos(request):
    """
    Lista todos los egresos registrados.
    """
    egresos = Egreso.objects.select_related('usuario', 'caja', 'categoria').all()
    return render(request, 'caja/lista_egresos.html', {
        'egresos': egresos,
    })


@login_required
@admin_required
def registrar_egreso(request):
    """
    Registra un nuevo egreso en la caja activa.
    """
    caja = AperturaCaja.objects.filter(activa=True).first()
    if not caja:
        messages.error(request, 'No hay una caja abierta.')
        return redirect('estado_caja')

    if request.method == 'POST':
        form = EgresoForm(request.POST, request.FILES)
        if form.is_valid():
            egreso = form.save(commit=False)
            egreso.caja = caja
            egreso.usuario = request.user
            egreso.save()
            messages.success(request, 'Egreso registrado correctamente.')
            return redirect('estado_caja')
    else:
        form = EgresoForm()

    return render(request, 'caja/form_egreso.html', {
        'form': form,
    })


@login_required
@admin_required
def editar_egreso(request, pk):
    """Edita un egreso existente."""
    egreso = get_object_or_404(Egreso, pk=pk)

    if request.method == 'POST':
        form = EgresoForm(request.POST, request.FILES, instance=egreso)
        if form.is_valid():
            form.save()
            messages.success(request, 'Egreso actualizado correctamente.')
            return redirect('lista_egresos')
    else:
        form = EgresoForm(instance=egreso)

    return render(request, 'caja/form_egreso.html', {
        'form': form, 'editando': True, 'egreso': egreso,
    })


@login_required
@admin_required
def eliminar_egreso(request, pk):
    """Elimina un egreso."""
    egreso = get_object_or_404(Egreso, pk=pk)
    egreso.delete()
    messages.success(request, 'Egreso eliminado correctamente.')
    return redirect('lista_egresos')


@login_required
@admin_required
def gestionar_categorias_egreso(request):
    """Gestiona las categorías de egreso."""
    categorias = CategoriaEgreso.objects.all()

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if nombre:
            if CategoriaEgreso.objects.filter(nombre__iexact=nombre).exists():
                messages.error(request, f'La categoría "{nombre}" ya existe.')
            else:
                CategoriaEgreso.objects.create(nombre=nombre)
                messages.success(request, f'Categoría "{nombre}" creada.')
        else:
            messages.error(request, 'El nombre no puede estar vacío.')
        return redirect('gestionar_categorias_egreso')

    return render(request, 'caja/gestionar_categorias_egreso.html', {
        'categorias': categorias,
    })


@login_required
@admin_required
def eliminar_categoria_egreso(request, pk):
    """Elimina una categoría de egreso."""
    categoria = get_object_or_404(CategoriaEgreso, pk=pk)
    if categoria.egresos.exists():
        messages.error(request, f'No se puede eliminar "{categoria.nombre}" porque tiene egresos asociados.')
    else:
        messages.success(request, f'Categoría "{categoria.nombre}" eliminada.')
        categoria.delete()
    return redirect('gestionar_categorias_egreso')
