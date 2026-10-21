"""
Vistas del módulo de seguimiento de créditos.

Permite listar los créditos, ver el detalle con su calendario de cuotas y
registrar abonos. Todas exigen el permiso `credito`.
"""
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.usuarios.decorators import permiso_required

from .forms import CreditoPreexistenteForm
from .models import Abono, Cliente, Credito
from .services import (
    abono_editable,
    caja_abierta,
    crear_credito_preexistente,
    editar_abono,
    enviar_recordatorio_cuota,
    enviar_recordatorio_credito,
    registrar_abono,
)


def _es_admin(user):
    """True si el usuario es administrador (is_staff o superuser)."""
    return bool(getattr(user, 'is_staff', False)
                or getattr(user, 'is_superuser', False))


@login_required
@permiso_required('credito')
def lista_creditos(request):
    """Listado de créditos con filtro por estado y búsqueda de cliente."""
    filtro = request.GET.get('estado', 'activos')
    q = (request.GET.get('q') or '').strip()

    creditos = Credito.objects.select_related('cliente', 'factura').prefetch_related('cuotas')

    if q:
        creditos = creditos.filter(
            Q(cliente__nombre__icontains=q)
            | Q(cliente__cedula__icontains=q)
            | Q(factura__numero__icontains=q)
        )

    if filtro == 'activos':
        creditos = creditos.filter(estado__in=['activo', 'vencido'])
    elif filtro == 'vencidos':
        creditos = creditos.filter(estado='vencido')
    elif filtro == 'pagados':
        creditos = creditos.filter(estado='pagado')

    # Resumen para las tarjetas superiores.
    todos = Credito.objects.all()
    resumen = {
        'activos': todos.filter(estado__in=['activo', 'vencido']).count(),
        'vencidos': todos.filter(estado='vencido').count(),
        'pagados': todos.filter(estado='pagado').count(),
        'saldo_total': todos.filter(estado__in=['activo', 'vencido'])
            .aggregate(t=Sum('saldo_pendiente'))['t'] or Decimal('0'),
        'saldo_vencido': sum((c.saldo_vencido for c in todos.filter(estado='vencido')), Decimal('0')),
    }

    return render(request, 'creditos/lista_creditos.html', {
        'creditos': creditos,
        'filtro': filtro,
        'q': q,
        'resumen': resumen,
    })


@login_required
@permiso_required('credito')
def vista_crear_credito_preexistente(request):
    """Da de alta un crédito ya existente (venta antigua no registrada)."""
    if request.method == 'POST':
        form = CreditoPreexistenteForm(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            try:
                credito = crear_credito_preexistente(
                    nombre_cliente=datos['nombre'],
                    monto=datos['monto'],
                    correo=datos.get('correo', ''),
                    observaciones=datos.get('observaciones', ''),
                    usuario=request.user,
                )
            except ValueError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(
                    request,
                    f'Crédito de {credito.cliente} por '
                    f'${credito.monto_total} registrado.')
                return redirect('detalle_credito', credito_id=credito.id)
    else:
        form = CreditoPreexistenteForm()

    return render(request, 'creditos/crear_credito_preexistente.html', {
        'form': form,
    })


@login_required
@permiso_required('credito')
def detalle_credito(request, credito_id):
    """Detalle de un crédito: calendario, abonos y formulario de abono."""
    credito = get_object_or_404(
        Credito.objects.select_related('cliente', 'factura').prefetch_related('cuotas', 'abonos'),
        pk=credito_id,
    )
    cuotas = credito.cuotas.order_by('numero')
    abonos = list(credito.abonos.select_related('usuario', 'cuota'))
    caja = caja_abierta()
    es_admin = _es_admin(request.user)
    for abono in abonos:
        abono.editable = es_admin or abono_editable(abono)
        abono.monto_maximo = credito.saldo_pendiente + abono.monto
    hoy = timezone.localdate()
    proxima_cuota = credito.proxima_cuota
    puede_enviar = (
        bool((credito.cliente.correo or '').strip())
        and credito.saldo_pendiente > 0
        and (proxima_cuota is not None or credito.es_preexistente)
    )

    return render(request, 'creditos/detalle_credito.html', {
        'credito': credito,
        'cuotas': cuotas,
        'abonos': abonos,
        'hoy': hoy,
        'saldo_vencido': credito.saldo_vencido,
        'puede_enviar': puede_enviar,
        'caja_activa': caja,
        'caja_abierta': caja is not None,
        'es_admin': es_admin,
    })


@login_required
@permiso_required('credito')
def vista_registrar_abono(request, credito_id):
    """Registra un abono contra un crédito (solo POST)."""
    credito = get_object_or_404(Credito, pk=credito_id)

    if request.method != 'POST':
        return redirect('detalle_credito', credito_id=credito_id)

    if credito.saldo_pendiente <= 0:
        messages.error(request, 'Este crédito ya está pagado por completo.')
        return redirect('detalle_credito', credito_id=credito_id)

    try:
        monto = Decimal(request.POST.get('monto', 0))
    except (InvalidOperation, ValueError):
        monto = Decimal('0')
    metodo = request.POST.get('metodo', 'efectivo')
    if metodo not in ('efectivo', 'transferencia'):
        metodo = 'efectivo'
    cuota_id = request.POST.get('cuota') or None
    observacion = (request.POST.get('observacion') or '').strip()

    if monto <= 0:
        messages.error(request, 'Ingresa un monto mayor a cero.')
        return redirect('detalle_credito', credito_id=credito_id)

    try:
        abono = registrar_abono(
            credito, monto, metodo=metodo, usuario=request.user,
            cuota_id=cuota_id, observacion=observacion,
        )
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect('detalle_credito', credito_id=credito_id)

    if credito.saldo_pendiente <= 0:
        messages.success(
            request,
            f'Abono de ${abono.monto} registrado. El crédito de '
            f'{credito.cliente} quedó pagado por completo.')
    else:
        messages.success(
            request,
            f'Abono de ${abono.monto} registrado. Saldo pendiente: '
            f'${credito.saldo_pendiente}.')
    return redirect('detalle_credito', credito_id=credito_id)


@login_required
@permiso_required('credito')
def vista_enviar_recordatorio(request, credito_id):
    """Envía a mano un recordatorio de la próxima cuota (solo POST)."""
    credito = get_object_or_404(
        Credito.objects.select_related('cliente'), pk=credito_id)

    if request.method != 'POST':
        return redirect('detalle_credito', credito_id=credito_id)

    correo = (credito.cliente.correo or '').strip()
    if not correo:
        messages.error(
            request,
            'El cliente no tiene correo registrado; no se puede enviar '
            'el recordatorio.')
        return redirect('detalle_credito', credito_id=credito_id)

    cuota = credito.proxima_cuota
    if cuota is None:
        if credito.es_preexistente:
            ok, detalle = enviar_recordatorio_credito(credito, 'manual')
            if ok:
                messages.success(
                    request,
                    f'Recordatorio de saldo pendiente enviado a {detalle}.')
            else:
                messages.error(
                    request, f'No se pudo enviar el recordatorio: {detalle}')
            return redirect('detalle_credito', credito_id=credito_id)
        messages.error(request, 'Este crédito no tiene cuotas pendientes.')
        return redirect('detalle_credito', credito_id=credito_id)

    ok, detalle = enviar_recordatorio_cuota(cuota, 'manual')
    if ok:
        messages.success(
            request,
            f'Recordatorio de la cuota {cuota.numero} enviado a {detalle}.')
    else:
        messages.error(request, f'No se pudo enviar el recordatorio: {detalle}')
    return redirect('detalle_credito', credito_id=credito_id)


@login_required
@permiso_required('credito')
def vista_editar_abono(request, credito_id, abono_id):
    """Modifica el monto de un abono (solo POST).

    Solo se permite mientras el abono pertenezca a la caja que sigue abierta.
    """
    credito = get_object_or_404(Credito, pk=credito_id)
    abono = get_object_or_404(Abono, pk=abono_id, credito=credito)

    if request.method != 'POST':
        return redirect('detalle_credito', credito_id=credito_id)

    try:
        nuevo_monto = Decimal(request.POST.get('monto', 0))
    except (InvalidOperation, ValueError):
        nuevo_monto = Decimal('0')

    metodo = request.POST.get('metodo')
    observar = request.POST.get('observacion')
    observacion = observar.strip() if observar is not None else None

    try:
        editar_abono(
            abono, nuevo_monto, usuario=request.user,
            metodo=metodo, observacion=observacion,
            forzar=_es_admin(request.user),
        )
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect('detalle_credito', credito_id=credito_id)

    messages.success(
        request,
        f'Abono actualizado a ${abono.monto} correctamente.')
    return redirect('detalle_credito', credito_id=credito_id)
