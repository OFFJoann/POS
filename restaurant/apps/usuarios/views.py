"""
Vistas de la aplicación usuarios.

Incluye autenticación por cédula y CRUD de vendedores.
"""
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import FormView
from django.urls import reverse_lazy
from django import forms
from django.db.models import Sum, F
from .models import Vendedor
from .forms import VendedorForm
from .decorators import admin_required
from apps.caja.models import AperturaCaja
from apps.ventas.models import Factura
from apps.productos.models import Producto
from apps.mesas.models import Mesa


class CedulaForm(forms.Form):
    """Formulario para autenticación por cédula."""
    cedula = forms.CharField(
        label='Cédula',
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-center',
            'placeholder': 'Ingresa tu cédula',
            'autofocus': True,
            'autocomplete': 'off',
        })
    )


class AccederView(FormView):
    """
    Vista para iniciar sesión con cédula.

    No requiere contraseña, solo el número de cédula.
    """
    template_name = 'auth/acceder.html'
    form_class = CedulaForm
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        """Autentica al usuario por cédula."""
        cedula = form.cleaned_data['cedula']
        user = authenticate(self.request, cedula=cedula)
        if user is not None:
            login(self.request, user)
            messages.success(self.request, f'Bienvenido {user.vendedor.nombre}!')
            return super().form_valid(form)
        messages.error(self.request, 'Cédula no encontrada o usuario inactivo.')
        return self.form_invalid(form)

    def get(self, request, *args, **kwargs):
        """Redirige al dashboard si ya está autenticado."""
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().get(request, *args, **kwargs)


def salir(request):
    """Cierra la sesión del usuario."""
    logout(request)
    messages.info(request, 'Sesión cerrada correctamente.')
    return redirect('acceder')


@login_required
def dashboard(request):
    """
    Dashboard principal del sistema.

    Muestra mesas, resumen de caja, ventas del día
    y productos con stock bajo.
    """
    if not hasattr(request.user, 'vendedor'):
        return redirect('acceder')

    vendedor = request.user.vendedor
    mesas = Mesa.objects.filter(activa=True)
    caja_activa = AperturaCaja.objects.filter(activa=True).first()

    hoy = Factura.objects.filter(created_at__date=date.today())
    ventas_hoy = hoy.aggregate(total=Sum('total'))['total'] or 0

    stock_bajo = Producto.objects.filter(
        estado='activo',
        stock_actual__lte=F('stock_minimo')
    )[:10]

    return render(request, 'usuarios/dashboard.html', {
        'vendedor': vendedor,
        'mesas': mesas,
        'caja_activa': caja_activa,
        'ventas_hoy': ventas_hoy,
        'stock_bajo': stock_bajo,
    })


@login_required
@admin_required
def lista_vendedores(request):
    """Lista todos los vendedores."""
    vendedores = Vendedor.objects.all()
    return render(request, 'usuarios/lista_vendedores.html', {
        'vendedores': vendedores,
    })


@login_required
@admin_required
def crear_vendedor(request):
    """Crea un nuevo vendedor."""
    if request.method == 'POST':
        form = VendedorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Vendedor creado correctamente.')
            return redirect('lista_vendedores')
    else:
        form = VendedorForm()
    return render(request, 'usuarios/form_vendedor.html', {
        'form': form, 'accion': 'Crear'
    })


@login_required
@admin_required
def editar_vendedor(request, pk):
    """Edita un vendedor existente."""
    vendedor = get_object_or_404(Vendedor, pk=pk)
    if request.method == 'POST':
        form = VendedorForm(request.POST, instance=vendedor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Vendedor actualizado correctamente.')
            return redirect('lista_vendedores')
    else:
        form = VendedorForm(instance=vendedor)
    return render(request, 'usuarios/form_vendedor.html', {
        'form': form, 'accion': 'Editar', 'vendedor': vendedor
    })


@login_required
@admin_required
def eliminar_vendedor(request, pk):
    """Elimina un vendedor."""
    vendedor = get_object_or_404(Vendedor, pk=pk)
    if request.method == 'POST':
        nombre = vendedor.nombre
        vendedor.usuario.delete()
        vendedor.delete()
        messages.success(request, f'Vendedor "{nombre}" eliminado correctamente.')
        return redirect('lista_vendedores')
    return render(request, 'usuarios/confirmar_eliminar.html', {
        'vendedor': vendedor
    })
