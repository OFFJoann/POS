"""
Vistas de la aplicación usuarios.

Incluye autenticación por correo/contraseña con 2FA opcional
y CRUD de vendedores.
"""
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import FormView, TemplateView
from django.urls import reverse_lazy
from django import forms
from django.db.models import Sum, F
from django.http import JsonResponse
import json
import base64
import io
import pyotp
import qrcode
from .models import Vendedor
from .forms import VendedorForm
from .decorators import admin_required
from apps.caja.models import AperturaCaja
from apps.ventas.models import Factura
from apps.productos.models import Producto
from apps.mesas.models import Mesa


class AccesoForm(forms.Form):
    """Formulario para autenticación por correo y contraseña."""
    email = forms.EmailField(
        label='Correo',
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'correo@empresa.com',
            'autofocus': True,
            'autocomplete': 'email',
        })
    )
    password = forms.CharField(
        label='Contraseña',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Tu contraseña',
            'autocomplete': 'current-password',
        })
    )


class AccederView(FormView):
    """
    Vista para iniciar sesión con correo y contraseña.

    Si el vendedor tiene 2FA activado (totp_secret), deriva a la
    verificación del código antes de completar el login.
    """
    template_name = 'auth/acceder.html'
    form_class = AccesoForm
    success_url = reverse_lazy('vista_mesas')

    def _completar_login(self, request, user):
        """Completa el login y redirige según el tour."""
        login(request, user)
        messages.success(request, f'Bienvenido {user.vendedor.nombre}!')
        if not user.vendedor.tour_completado:
            return redirect('tour_capacitacion')
        return redirect('vista_mesas')

    def form_valid(self, form):
        """Autentica al usuario por correo y contraseña."""
        email = form.cleaned_data['email'].strip().lower()
        password = form.cleaned_data['password']
        user = authenticate(self.request, email=email, password=password)
        if user is not None:
            vendedor = getattr(user, 'vendedor', None)
            if vendedor and vendedor.totp_secret:
                # Paso 1 completo: falta el código 2FA.
                self.request.session['2fa_user'] = user.pk
                return redirect('verificar_2fa')
            return self._completar_login(self.request, user)
        messages.error(self.request, 'Correo o contraseña incorrectos.')
        form.add_error(None, 'Correo o contraseña incorrectos.')
        return self.form_invalid(form)

    def get(self, request, *args, **kwargs):
        """Redirige a mesas si ya está autenticado."""
        if request.user.is_authenticated:
            if hasattr(request.user, 'vendedor') and not request.user.vendedor.tour_completado:
                return redirect('tour_capacitacion')
            return redirect('vista_mesas')
        return super().get(request, *args, **kwargs)


class Verificar2FAView(TemplateView):
    """
    Muestra y valida el código TOTP como segundo factor.

    Requiere que en sesión exista '2fa_user' (puesto por AccederView).
    """
    template_name = 'auth/verificar_2fa.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if 'error' not in ctx:
            ctx['error'] = self.request.session.get('2fa_error')
            self.request.session.pop('2fa_error', None)
        user_id = self.request.session.get('2fa_user')
        user = None
        if user_id:
            from django.contrib.auth.models import User
            user = User.objects.filter(pk=user_id).first()
        ctx['correo'] = user.email if (user and hasattr(user, 'vendedor')) else ''
        return ctx

    def post(self, request, *args, **kwargs):
        user_id = request.session.get('2fa_user')
        if not user_id:
            return redirect('acceder')
        from django.contrib.auth.models import User
        user = User.objects.filter(pk=user_id).first()
        vendedor = getattr(user, 'vendedor', None) if user else None
        if not vendedor or not vendedor.totp_secret:
            request.session.pop('2fa_user', None)
            return redirect('acceder')

        codigo = request.POST.get('codigo', '').strip()
        totp = pyotp.TOTP(vendedor.totp_secret)
        if totp.verify(codigo, valid_window=1):
            request.session.pop('2fa_user', None)
            return self._completar_login(request, user)
        request.session['2fa_error'] = 'Código incorrecto o vencido.'
        return redirect('verificar_2fa')

    def _completar_login(self, request, user):
        login(request, user)
        messages.success(request, f'Bienvenido {user.vendedor.nombre}!')
        if not user.vendedor.tour_completado:
            return redirect('tour_capacitacion')
        return redirect('vista_mesas')


def salir(request):
    """Cierra la sesión del usuario."""
    logout(request)
    messages.info(request, 'Sesión cerrada correctamente.')
    return redirect('acceder')


def _generar_qr(totp_uri):
    """Genera un QR en base64 a partir de una URI TOTP."""
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


def _otp_uri(vendedor, emisor='El Choli'):
    """Construye la URI otpauth:// para la app de autenticación."""
    return pyotp.totp.TOTP(vendedor.totp_secret).provisioning_uri(
        name=vendedor.email or vendedor.cedula,
        issuer_name=emisor)


@login_required
@admin_required
def configurar_2fa(request, pk):
    """
    Activa o desactiva el 2FA de un vendedor.

    GET: muestra el QR y el secreto si está activo.
    POST:
      - 'activar'  → genera un secreto TOTP nuevo (o conserva el actual)
      - 'desactivar' → limpia el secreto (2FA desactivado)
    """
    vendedor = get_object_or_404(Vendedor, pk=pk)
    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'desactivar':
            vendedor.totp_secret = ''
            vendedor.save(update_fields=['totp_secret'])
            messages.success(request, '2FA desactivado para el vendedor.')
            return redirect('editar_vendedor', pk=pk)
        if accion == 'activar' and not vendedor.totp_secret:
            vendedor.totp_secret = pyotp.random_base32()
            vendedor.save(update_fields=['totp_secret'])
            messages.success(request, '2FA activado. Escanea el código QR.')
        elif accion == 'regenerar':
            vendedor.totp_secret = pyotp.random_base32()
            vendedor.save(update_fields=['totp_secret'])
            messages.success(request, 'Secreto 2FA regenerado. Escanea el nuevo código QR.')

    ctx = {'vendedor': vendedor, 'qr_b64': None, 'otp_uri': None}
    if vendedor.totp_secret:
        ctx['otp_uri'] = _otp_uri(vendedor)
        ctx['qr_b64'] = _generar_qr(ctx['otp_uri'])
    return render(request, 'usuarios/configurar_2fa.html', ctx)


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
    permisos = [(form[datos[0]], datos[2]) for datos in Vendedor.permisos_para_form()]
    return render(request, 'usuarios/form_vendedor.html', {
        'form': form, 'accion': 'Crear', 'permisos': permisos
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
    permisos = [(form[datos[0]], datos[2]) for datos in Vendedor.permisos_para_form()]
    return render(request, 'usuarios/form_vendedor.html', {
        'form': form, 'accion': 'Editar', 'vendedor': vendedor, 'permisos': permisos
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


@login_required
def tour_capacitacion(request):
    """Muestra el tour de capacitación al usuario."""
    vendedor = getattr(request.user, 'vendedor', None)
    if not vendedor:
        return redirect('acceder')
    
    permisos = [codigo for codigo in Vendedor.PERMISOS if vendedor.puede(codigo)]
    
    return render(request, 'usuarios/tour_capacitacion.html', {
        'vendedor': vendedor,
        'permisos_json': json.dumps(permisos),
    })


@login_required
def completar_tour(request):
    """Marca el tour como completado."""
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    vendedor = getattr(request.user, 'vendedor', None)
    if not vendedor:
        return JsonResponse({'ok': False}, status=400)
    vendedor.tour_completado = True
    vendedor.save(update_fields=['tour_completado'])
    return JsonResponse({'ok': True})
