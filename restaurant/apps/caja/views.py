"""
Vistas de la aplicación caja.

Incluye apertura, cierre de caja y gestión de egresos.
"""
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import AperturaCaja, CierreCaja, Egreso, CategoriaEgreso
from .forms import AperturaCajaForm, EgresoForm
from apps.usuarios.decorators import admin_required, permiso_required
from apps.mesas.models import Mesa


def _puede_ver_totales(user):
    """Indica si el usuario puede ver los totales/dinero esperado de caja."""
    if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
        return True
    v = getattr(user, 'vendedor', None)
    return bool(v and v.puede('ver_totales_caja'))


@login_required
@permiso_required('caja')
def estado_caja(request):
    """
    Muestra el estado actual de la caja.

    Si hay una caja abierta, muestra sus movimientos.
    """
    caja_activa = AperturaCaja.objects.filter(activa=True).first()
    egresos = Egreso.objects.none()
    comisiones = []
    total_comisiones = 0
    falta_por_cobrar = 0

    if caja_activa:
        egresos = caja_activa.egresos.select_related('usuario', 'categoria').all()
        from apps.ventas.services import comisiones_por_vendedor
        from apps.mesas.models import Pedido
        from django.db.models import Sum, Case, When, F
        comisiones = comisiones_por_vendedor(
            caja_activa.fecha_apertura, caja_activa._fecha_fin
        )
        total_comisiones = sum((c['total'] or 0) for c in comisiones)
        falta_por_cobrar = Pedido.objects.filter(
            estado__in=['activo', 'parcial']
        ).aggregate(
            total=Sum(
                Case(
                    When(estado='parcial', then=F('saldo_pendiente')),
                    default=F('total'),
                )
            )
        )['total'] or 0

    ya_cobrado = caja_activa.total_ventas if caja_activa else 0
    total_proyectado = ya_cobrado + falta_por_cobrar

    return render(request, 'caja/estado_caja.html', {
        'caja': caja_activa,
        'egresos': egresos,
        'comisiones': comisiones,
        'total_comisiones': total_comisiones,
        'ya_cobrado': ya_cobrado,
        'falta_por_cobrar': falta_por_cobrar,
        'total_proyectado': total_proyectado,
        'puede_ver_totales': _puede_ver_totales(request.user),
    })


@login_required
@permiso_required('caja')
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
@permiso_required('caja')
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

    from apps.ventas.services import comisiones_por_vendedor
    from apps.mesas.models import Pedido, SolicitudPedido
    from django.db.models import Sum, Case, When, F
    comisiones = comisiones_por_vendedor(caja.fecha_apertura, caja._fecha_fin)
    total_comisiones = sum((c['total'] or 0) for c in comisiones)
    falta_por_cobrar = Pedido.objects.filter(
        estado__in=['activo', 'parcial']
    ).aggregate(
        total=Sum(
            Case(
                When(estado='parcial', then=F('saldo_pendiente')),
                default=F('total'),
            )
        )
    )['total'] or 0
    ya_cobrado = caja.total_ventas
    total_proyectado = ya_cobrado + falta_por_cobrar
    comisiones_detalle = [
        {
            'id': c['id'],
            'nombre': c['nombre'],
            'apellidos': c['apellidos'],
            'total': float(c['total'] or 0),
            'items': float(c['items'] or 0),
            'lineas': [
                {
                    'producto': l['producto'],
                    'cantidad': float(l['cantidad'] or 0),
                    'comision': float(l['comision'] or 0),
                }
                for l in c['lineas']
            ],
        }
        for c in comisiones
    ]

    puede_ver = _puede_ver_totales(request.user)

    if request.method == 'POST':
        efectivo_conteo = Decimal(request.POST.get('efectivo_conteo', 0))

        caja.activa = False
        caja.fecha_cierre = timezone.now()
        caja.save()

        CierreCaja.objects.create(
            caja=caja,
            usuario=request.user,
            monto_inicial=0,
            total_ventas_efectivo=caja.total_ventas_efectivo,
            total_ventas_transferencia=caja.total_ventas_transferencia,
            total_ventas=caja.total_ventas,
            total_egresos=caja.total_egresos,
            total_egresos_efectivo=caja.total_egresos_efectivo,
            total_egresos_transferencia=caja.total_egresos_transferencia,
            total_comisiones=total_comisiones,
            comisiones_detalle=comisiones_detalle,
            dinero_esperado=caja.dinero_esperado,
            efectivo_conteo=efectivo_conteo,
            diferencia=efectivo_conteo - caja.dinero_esperado,
        )

        if puede_ver:
            messages.success(
                request,
                f'Caja cerrada. Dinero esperado: ${caja.dinero_esperado:0f}'
            )
        else:
            messages.success(request, 'Caja cerrada correctamente.')

        # Limpiar las notificaciones de "Pedidos de vendedores" al cerrar la
        # caja, para no arrastrar avisos de días anteriores. Los detalles
        # quedan sin vincular (SET_NULL) y no afecta las ventas ya cobradas.
        SolicitudPedido.objects.all().delete()

        return redirect('consolidados')

    return render(request, 'caja/confirmar_cierre.html', {
        'caja': caja,
        'comisiones': comisiones,
        'total_comisiones': total_comisiones,
        'ya_cobrado': ya_cobrado,
        'falta_por_cobrar': falta_por_cobrar,
        'total_proyectado': total_proyectado,
        'puede_ver_totales': puede_ver,
    })


@login_required
@permiso_required('caja')
def lista_consolidados(request):
    """
    Muestra el historial de cierres de caja consolidados.
    """
    from collections import defaultdict
    from django.db.models import Sum
    from django.db.models.functions import ExtractHour
    from apps.ventas.models import Pago

    cierres = CierreCaja.objects.all().order_by('-fecha_cierre')

    datos_cierres = []
    for c in cierres:
        facturas = c.facturas_del_dia.select_related('mesa', 'mesero').prefetch_related('pedido__detalles__producto')

        # Agrupar facturas por mesa
        mesas_dict = defaultdict(list)
        for f in facturas:
            mesas_dict[f.mesa.numero].append(f)

        mesas_agrupadas = []
        for mesa_num in sorted(mesas_dict.keys()):
            facturas_mesa = mesas_dict[mesa_num]
            total_mesa = sum(f.total for f in facturas_mesa)
            mesas_agrupadas.append({
                'numero': mesa_num,
                'facturas': facturas_mesa,
                'total': total_mesa,
            })

        # Resumen general de productos vendidos
        productos_resumen = defaultdict(lambda: {'cantidad': 0, 'total': 0})
        for f in facturas:
            for d in f.pedido.detalles.all():
                nombre = d.producto.nombre
                productos_resumen[nombre]['cantidad'] += d.cantidad
                productos_resumen[nombre]['total'] += d.subtotal

        productos_lista = sorted(
            [{'nombre': k, 'cantidad': v['cantidad'], 'total': v['total']}
             for k, v in productos_resumen.items()],
            key=lambda x: x['cantidad'],
            reverse=True,
        )

        # Ventas por hora (entre apertura y cierre)
        pagos_hora = (
            Pago.objects.filter(
                created_at__gte=c.caja.fecha_apertura,
                created_at__lte=c.fecha_cierre,
            )
            .annotate(hora=ExtractHour('created_at'))
            .values('hora')
            .annotate(total=Sum('monto'))
            .order_by('hora')
        )
        ventas_por_hora = {item['hora']: float(item['total']) for item in pagos_hora}

        # Rango completo de horas entre apertura y cierre
        hora_apertura = c.caja.fecha_apertura.hour
        hora_cierre = c.fecha_cierre.hour
        if hora_cierre < hora_apertura:
            horas_rango = list(range(hora_apertura, 24)) + list(range(0, hora_cierre + 1))
        else:
            horas_rango = list(range(hora_apertura, hora_cierre + 1))

        grafico_horas = []
        max_venta = max(ventas_por_hora.values()) if ventas_por_hora else 1
        for h in horas_rango:
            venta = ventas_por_hora.get(h, 0)
            porcentaje = (venta / max_venta * 100) if max_venta > 0 else 0
            grafico_horas.append({
                'hora': str(h),
                'venta': venta,
                'porcentaje': round(porcentaje, 1),
            })

        datos_cierres.append({
            'cierre': c,
            'mesas': mesas_agrupadas,
            'productos': productos_lista,
            'total_facturas': facturas.count(),
            'grafico_horas': grafico_horas,
        })

    return render(request, 'caja/consolidados.html', {
        'datos_cierres': datos_cierres,
        'puede_ver_totales': _puede_ver_totales(request.user),
    })


@login_required
@permiso_required('caja')
def lista_egresos(request):
    """
    Lista todos los egresos registrados.
    """
    egresos = Egreso.objects.select_related('usuario', 'caja', 'categoria').all()
    return render(request, 'caja/lista_egresos.html', {
        'egresos': egresos,
    })


@login_required
@permiso_required('caja')
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
@permiso_required('caja')
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
@permiso_required('caja')
def eliminar_egreso(request, pk):
    """Elimina un egreso."""
    egreso = get_object_or_404(Egreso, pk=pk)
    egreso.delete()
    messages.success(request, 'Egreso eliminado correctamente.')
    return redirect('lista_egresos')


@login_required
@permiso_required('caja')
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
@permiso_required('caja')
def eliminar_categoria_egreso(request, pk):
    """Elimina una categoría de egreso."""
    categoria = get_object_or_404(CategoriaEgreso, pk=pk)
    if categoria.egresos.exists():
        messages.error(request, f'No se puede eliminar "{categoria.nombre}" porque tiene egresos asociados.')
    else:
        messages.success(request, f'Categoría "{categoria.nombre}" eliminada.')
        categoria.delete()
    return redirect('gestionar_categorias_egreso')
