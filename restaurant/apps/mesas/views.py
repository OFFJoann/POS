"""
Vistas de la aplicación mesas.

Incluye la interfaz visual de mesas y la gestión de pedidos (POS).
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from django.db.models import Max, Prefetch
from .models import Mesa, Pedido, DetallePedido, SolicitudPedido
from .services import (
    crear_pedido, agregar_producto_a_pedido,
    modificar_cantidad, eliminar_detalle, actualizar_cantidad_detalle,
    aplicar_descuento, cerrar_pedido
)
from .forms import AgregarProductoForm, DescuentoForm, MesaForm
from apps.productos.models import Producto, Categoria
from apps.usuarios.decorators import admin_required, permiso_required
from apps.usuarios.models import Vendedor


def _autorizado_pedido(user, pedido, codigo, request):
    """Verifica que el usuario pueda ejecutar `codigo` sobre `pedido`.

    Administradores: siempre. Otros: debe ser dueño del pedido (o tener el
    permiso 'modificar_otros_pedidos') y tener el permiso `codigo`.
    """
    if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
        return True
    vendedor = getattr(user, 'vendedor', None)
    if not vendedor or not vendedor.activo:
        messages.error(request, 'No tienes permiso para realizar esta acción.')
        return False
    if pedido.mesero_id != vendedor.id and not vendedor.puede('modificar_otros_pedidos'):
        messages.error(request, 'No puedes modificar pedidos de otros vendedores.')
        return False
    if not vendedor.puede(codigo):
        messages.error(request, 'No tienes permiso para realizar esta acción.')
        return False
    return True


def _puede_cortesia_o_precio(user, request, permitir_cortesia, permitir_precio):
    """Aplica las restricciones de cortesía/precio a nivel de servidor.

    Devuelve (cortesia_permitida, precio_permitido) según el vendedor.
    """
    if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
        return True, True
    vendedor = getattr(user, 'vendedor', None)
    if not vendedor:
        return False, False
    return (
        bool(permitir_cortesia and vendedor.puede('cortesia')),
        bool(permitir_precio and vendedor.puede('cambiar_precio')),
    )
from apps.ventas.models import Factura, Pago
from apps.caja.models import AperturaCaja


def _tiene_vendedor(user):
    """Verifica que el usuario tenga perfil de vendedor."""
    return hasattr(user, 'vendedor') and user.vendedor.activo


@login_required
def vista_mesas(request):
    """
    Vista principal de mesas.

    Muestra todas las mesas como tarjetas grandes con
    colores según su estado.
    """
    mesas = Mesa.objects.filter(activa=True).order_by('numero').prefetch_related(
        Prefetch(
            'pedidos',
            queryset=Pedido.objects.filter(estado='activo').select_related('mesero'),
            to_attr='pedidos_activos'
        )
    )
    categorias = Categoria.objects.filter(activo=True).order_by('orden', 'nombre')
    return render(request, 'mesas/vista_mesas.html', {
        'mesas': mesas,
        'categorias': categorias,
    })


@login_required
@admin_required
def gestion_mesas(request):
    """Lista todas las mesas y permite crear nuevas."""
    mesas = Mesa.objects.all().order_by('numero')

    if request.method == 'POST':
        form = MesaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'Mesa {form.cleaned_data["numero"]} creada.')
            return redirect('gestion_mesas')
    else:
        form = MesaForm()

    return render(request, 'mesas/gestion_mesas.html', {
        'mesas': mesas,
        'form': form,
    })


@login_required
@admin_required
def eliminar_mesa(request, mesa_id):
    """Elimina una mesa (solo si está libre)."""
    mesa = get_object_or_404(Mesa, pk=mesa_id)
    if mesa.estado != 'libre':
        messages.error(request, f'No se puede eliminar la Mesa {mesa.numero} porque no está libre.')
        return redirect('gestion_mesas')
    Mesa.objects.filter(pk=mesa_id).delete()
    messages.success(request, f'Mesa {mesa.numero} eliminada.')
    return redirect('gestion_mesas')


@login_required
def estado_mesas_api(request):
    """
    API que retorna el estado de todas las mesas en JSON.
    Útil para actualización en tiempo real.
    """
    mesas = Mesa.objects.filter(activa=True).order_by('numero')
    data = []
    for mesa in mesas:
        pedido_activo = mesa.pedidos.filter(estado='activo').first()
        data.append({
            'id': mesa.id,
            'numero': mesa.numero,
            'estado': mesa.estado,
            'estado_display': mesa.get_estado_display(),
            'tiene_pedido': pedido_activo is not None,
            'pedido_id': pedido_activo.id if pedido_activo else None,
            'mesero': str(pedido_activo.mesero) if pedido_activo else None,
            'total': float(pedido_activo.total) if pedido_activo else 0,
        })
    return JsonResponse({'mesas': data})


@login_required
@permiso_required('facturar')
def abrir_pedido(request, mesa_id):
    """
    Abre un nuevo pedido en la mesa o redirige al existente.
    Solo permite abrir pedido nuevo si la mesa está libre.
    """
    if not _tiene_vendedor(request.user):
        messages.error(request, 'Perfil de vendedor no encontrado.')
        return redirect('acceder')

    mesa = get_object_or_404(Mesa, pk=mesa_id, activa=True)
    vendedor = request.user.vendedor

    # Redirigir al pedido activo o con pago parcial si existe
    pedido_existente = mesa.pedidos.filter(estado__in=['activo', 'parcial']).first()
    if pedido_existente:
        return redirect('detalle_pedido', pedido_id=pedido_existente.id)

    # Solo se puede abrir pedido nuevo si la mesa está libre
    if mesa.estado not in ('libre',):
        mensajes = {
            'pagada': 'Esta mesa ya fue pagada. Límpiala para abrir un nuevo pedido.',
            'cerrada': 'Esta mesa está cerrada.',
            'activo': 'Ya hay un pedido activo en esta mesa.',
        }
        messages.warning(request, mensajes.get(mesa.estado, 'No se puede abrir pedido en esta mesa.'))
        return redirect('vista_mesas')

    pedido = crear_pedido(mesa, vendedor)
    messages.success(request, f'Pedido abierto en Mesa {mesa.numero}')
    return redirect('detalle_pedido', pedido_id=pedido.id)


@login_required
def detalle_pedido(request, pedido_id):
    """
    Vista detalle del pedido (POS).

    Muestra los productos agregados, totales y permite
    agregar más productos, modificar cantidades y cobrar.
    """
    if not _tiene_vendedor(request.user):
        messages.error(request, 'Perfil de vendedor no encontrado.')
        return redirect('acceder')

    pedido = get_object_or_404(
        Pedido.objects.select_related('mesa', 'mesero'),
        pk=pedido_id
    )

    # Inicia la sesión cuando el mesero entra a la mesa por primera vez.
    # Solo se setea una vez: al cargar la página. No se resetea en
    # recargas (F5), redirecciones ni navegación posterior.
    if request.method == 'GET' and pedido.sesion_inicio is None:
        pedido.sesion_inicio = timezone.now()
        pedido.save(update_fields=['sesion_inicio'])

    # Verificar permisos
    if not (request.user.is_staff or request.user.is_superuser):
        v = getattr(request.user, 'vendedor', None)
        if not v or (pedido.mesero_id != v.id
                     and not v.puede('modificar_otros_pedidos')):
            messages.error(request, 'No puedes modificar pedidos de otros vendedores.')
            return redirect('vista_mesas')

    categorias = Categoria.objects.filter(activo=True).order_by('orden', 'nombre')
    productos_por_categoria = {}
    for cat in categorias:
        prods = Producto.objects.filter(categoria=cat, estado='activo')
        if prods.exists():
            productos_por_categoria[cat] = prods

    form_producto = AgregarProductoForm()
    form_descuento = DescuentoForm()
    vendedores = Vendedor.objects.filter(activo=True)

    return render(request, 'mesas/detalle_pedido.html', {
        'pedido': pedido,
        'detalles': pedido.detalles.select_related('producto').all(),
        'productos_por_categoria': productos_por_categoria,
        'categorias': categorias,
        'form_producto': form_producto,
        'form_descuento': form_descuento,
        'vendedores': vendedores,
    })


@login_required
def agregar_producto(request, pedido_id):
    """
    Agrega un producto al pedido vía AJAX o POST normal.
    """
    pedido = get_object_or_404(Pedido, pk=pedido_id)

    if pedido.estado not in ('activo', 'parcial'):
        messages.error(request, 'No se pueden agregar productos a un pedido pagado o cerrado.')
        return redirect('detalle_pedido', pedido_id=pedido_id)

    if not _autorizado_pedido(request.user, pedido, 'facturar', request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Permiso denegado'}, status=403)
        return redirect('vista_mesas')

    if request.method == 'POST':
        producto_id = request.POST.get('producto_id')
        cantidad = Decimal(request.POST.get('cantidad', 1))
        cortesia = request.POST.get('cortesia') == 'true'
        precio_str = request.POST.get('precio_unitario', '').strip()
        precio_personalizado = Decimal(precio_str) if precio_str else None

        # Restricciones de cortesía y cambio de precio a nivel de servidor
        cortesia_ok, precio_ok = _puede_cortesia_o_precio(
            request.user, request, cortesia, precio_personalizado is not None)
        if not cortesia_ok:
            cortesia = False
        if not precio_ok:
            precio_personalizado = None

        try:
            detalle = agregar_producto_a_pedido(
                pedido, producto_id, cantidad,
                cortesia=cortesia, precio_personalizado=precio_personalizado,
            )
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'detalle_id': detalle.id,
                    'producto': detalle.producto.nombre,
                    'cantidad': float(detalle.cantidad),
                    'precio_unitario': float(detalle.precio_unitario),
                    'subtotal': float(detalle.subtotal),
                    'total_pedido': float(pedido.total),
                })
            messages.success(request, 'Producto agregado al pedido.')
        except Producto.DoesNotExist:
            messages.error(request, 'Producto no encontrado.')

    return redirect('detalle_pedido', pedido_id=pedido_id)


@login_required
def quitar_producto(request, pedido_id, detalle_id):
    """
    Elimina o reduce la cantidad de un producto del pedido.
    """
    if request.method == 'POST':
        detalle = get_object_or_404(DetallePedido, pk=detalle_id, pedido_id=pedido_id)
        if detalle.pedido.estado not in ('activo', 'parcial'):
            messages.error(request, 'No se puede modificar un pedido pagado o cerrado.')
            return redirect('detalle_pedido', pedido_id=pedido_id)
        if not _autorizado_pedido(request.user, detalle.pedido, 'facturar', request):
            messages.error(request, 'Permiso denegado.')
            return redirect('vista_mesas')

        precio_unitario = request.POST.get('precio_unitario')
        if precio_unitario:
            _, precio_ok = _puede_cortesia_o_precio(request.user, request, False, True)
            if not precio_ok:
                messages.error(request, 'No tienes permiso para cambiar precios.')
                return redirect('detalle_pedido', pedido_id=pedido_id)
            detalle.precio_unitario = Decimal(precio_unitario)
            detalle.subtotal = detalle.cantidad * detalle.precio_unitario
            detalle.save()
            detalle.pedido.calcular_totales()
            messages.success(request, 'Precio actualizado.')
            return redirect('detalle_pedido', pedido_id=pedido_id)

        nueva_cantidad = request.POST.get('cantidad')
        if nueva_cantidad and Decimal(nueva_cantidad) > 0:
            actualizar_cantidad_detalle(detalle, Decimal(nueva_cantidad))
            messages.success(request, 'Cantidad actualizada.')
        else:
            eliminar_detalle(detalle_id)
            messages.success(request, 'Producto eliminado del pedido.')

    return redirect('detalle_pedido', pedido_id=pedido_id)


@login_required
def aplicar_descuento(request, pedido_id):
    """
    Aplica un descuento al pedido.
    Solo administradores pueden aplicar descuentos.
    """
    v = getattr(request.user, 'vendedor', None)
    if not (request.user.is_staff or request.user.is_superuser
            or (v and v.puede('descuento'))):
        messages.error(request, 'No tienes permiso para aplicar descuentos.')
        return redirect('detalle_pedido', pedido_id=pedido_id)

    pedido = get_object_or_404(Pedido, pk=pedido_id)
    if request.method == 'POST':
        form = DescuentoForm(request.POST)
        if form.is_valid():
            descuento = form.cleaned_data['descuento']
            if descuento <= pedido.subtotal:
                aplicar_descuento(pedido, descuento)
                messages.success(request, f'Descuento de ${descuento} aplicado.')
            else:
                messages.error(request, 'El descuento no puede superar el subtotal.')

    return redirect('detalle_pedido', pedido_id=pedido_id)


@login_required
def guardar_observaciones(request, pedido_id):
    """Guarda las observaciones del pedido."""
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    if request.method == 'POST':
        observaciones = request.POST.get('observaciones', '')
        pedido.observaciones = observaciones
        pedido.save()
        messages.success(request, 'Observaciones guardadas.')
    return redirect('detalle_pedido', pedido_id=pedido_id)


@login_required
@transaction.atomic
def cobrar_pedido(request, pedido_id):
    """
    Procesa el cobro completo de un pedido.

    Genera factura, registra pago y descuenta inventario.
    """
    from apps.caja.models import AperturaCaja
    es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if not AperturaCaja.objects.filter(activa=True).exists():
        if es_ajax:
            return JsonResponse({'ok': False, 'error': 'No se puede facturar porque la caja está cerrada.'})
        messages.error(request, 'No se puede facturar porque la caja está cerrada.')
        return redirect('detalle_pedido', pedido_id=pedido_id)

    pedido = get_object_or_404(
        Pedido.objects.select_related('mesa', 'mesero'),
        pk=pedido_id
    )

    if not _autorizado_pedido(request.user, pedido, 'facturar', request):
        if es_ajax:
            return JsonResponse({'ok': False, 'error': 'No tienes permiso.'})
        return redirect('vista_mesas')

    if request.method == 'POST':
        metodo_pago = request.POST.get('metodo_pago')
        monto_a_cobrar = pedido.falta_por_cobrar
        valor_recibido = Decimal(request.POST.get('valor_recibido', 0))

        # Mesa ya pagada por completo (p. ej. con varios pagos parciales que
        # sumaron el total, o pedidos heredados con saldo 0). Se cierra sin
        # registrar un pago de $0 y queda libre.
        if monto_a_cobrar <= 0:
            factura = pedido.factura if pedido.estado == 'parcial' else None
            if factura:
                factura.es_parcial = False
                factura.saldo_pendiente = 0
                factura.valor_recibido = factura.total
                factura.save()
            pedido.estado = 'pagado'
            pedido.saldo_pendiente = 0
            pedido.fecha_cierre = timezone.now()
            pedido.save()
            pedido.mesa.estado = 'libre'
            pedido.mesa.save()
            if es_ajax:
                return JsonResponse({
                    'ok': True,
                    'factura_id': factura.id if factura else 0,
                    'numero': factura.numero if factura else 0,
                    'cambio': 0,
                    'mesa': pedido.mesa.numero,
                    'pagado': True,
                })
            if factura:
                messages.success(
                    request,
                    f'Mesa {pedido.mesa.numero} libre. Factura #{factura.numero} '
                    f'pagada por completo con pagos parciales.'
                )
                return redirect('ver_factura', factura_id=factura.id)
            messages.success(request, f'Mesa {pedido.mesa.numero} libre.')
            return redirect('vista_mesas')

        if metodo_pago not in ['efectivo', 'transferencia', 'cortesia']:
            if es_ajax:
                return JsonResponse({'ok': False, 'error': 'Método de pago inválido.'})
            messages.error(request, 'Método de pago inválido.')
            return redirect('detalle_pedido', pedido_id=pedido_id)

        if metodo_pago == 'cortesia':
            cortesia_ok, _ = _puede_cortesia_o_precio(request.user, request, True, False)
            if not cortesia_ok:
                if es_ajax:
                    return JsonResponse({'ok': False, 'error': 'No tienes permiso para cobrar como cortesía.'})
                messages.error(request, 'No tienes permiso para cobrar como cortesía.')
                return redirect('detalle_pedido', pedido_id=pedido_id)

        if valor_recibido < monto_a_cobrar:
            if es_ajax:
                return JsonResponse({'ok': False, 'error': 'El valor recibido es menor al monto a cobrar.'})
            messages.error(request, 'El valor recibido es menor al monto a cobrar.')
            return redirect('detalle_pedido', pedido_id=pedido_id)

        cambio = valor_recibido - monto_a_cobrar

        # Crear o actualizar factura
        if pedido.estado == 'parcial':
            factura = pedido.factura
            factura.metodo_pago = metodo_pago
            factura.total = pedido.total
            factura.valor_recibido = valor_recibido
            factura.cambio = cambio
            factura.es_parcial = False
            factura.saldo_pendiente = 0
            factura.save()
        else:
            ultimo_numero = Factura.objects.aggregate(maximo=Max('numero'))['maximo'] or 0
            factura = Factura(
                numero=ultimo_numero + 1,
                pedido=pedido,
                mesa=pedido.mesa,
                mesero=pedido.mesero,
                metodo_pago=metodo_pago,
                subtotal=pedido.subtotal,
                descuento=pedido.descuento,
                total=monto_a_cobrar,
                valor_recibido=valor_recibido,
                cambio=cambio,
            )
            factura._skip_inventory_deduction = True
            factura.save()

            # Descontar inventario (los combos descuentan sus componentes)
            from apps.inventario.services import descontar_pedido
            descontar_pedido(pedido)

        # Registrar pago
        Pago.objects.create(
            factura=factura,
            pedido=pedido,
            metodo=metodo_pago,
            monto=monto_a_cobrar,
            valor_recibido=valor_recibido,
            cambio=cambio,
            usuario=request.user,
        )

        # Actualizar estado
        pedido.estado = 'pagado'
        pedido.saldo_pendiente = 0
        pedido.fecha_cierre = timezone.now()
        pedido.save()

        # La mesa queda libre automáticamente al facturar el pedido completo
        pedido.mesa.estado = 'libre'
        pedido.mesa.save()

        if es_ajax:
            return JsonResponse({
                'ok': True,
                'factura_id': factura.id,
                'numero': factura.numero,
                'cambio': float(cambio),
                'mesa': pedido.mesa.numero,
            })
        messages.success(
            request,
            f'Factura #{factura.numero} generada. Cambio: ${cambio}. '
            f'Mesa {pedido.mesa.numero} libre.'
        )
        return redirect('ver_factura', factura_id=factura.id)

    return redirect('detalle_pedido', pedido_id=pedido_id)


@login_required
@transaction.atomic
def pago_parcial(request, pedido_id):
    """
    Procesa un pago parcial.

    El pedido queda con saldo pendiente.
    """
    from apps.caja.models import AperturaCaja
    es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if not AperturaCaja.objects.filter(activa=True).exists():
        if es_ajax:
            return JsonResponse({'ok': False, 'error': 'No se puede facturar porque la caja está cerrada.'})
        messages.error(request, 'No se puede facturar porque la caja está cerrada.')
        return redirect('detalle_pedido', pedido_id=pedido_id)

    pedido = get_object_or_404(Pedido, pk=pedido_id)

    if not _autorizado_pedido(request.user, pedido, 'facturar', request):
        if es_ajax:
            return JsonResponse({'ok': False, 'error': 'No tienes permiso.'})
        return redirect('vista_mesas')

    if request.method == 'POST':
        metodo_pago = request.POST.get('metodo_pago')
        monto_pago = Decimal(request.POST.get('monto_pago', 0))

        if metodo_pago not in ['efectivo', 'transferencia', 'cortesia']:
            if es_ajax:
                return JsonResponse({'ok': False, 'error': 'Método de pago inválido.'})
            messages.error(request, 'Método de pago inválido.')
            return redirect('detalle_pedido', pedido_id=pedido_id)

        if metodo_pago == 'cortesia':
            cortesia_ok, _ = _puede_cortesia_o_precio(request.user, request, True, False)
            if not cortesia_ok:
                if es_ajax:
                    return JsonResponse({'ok': False, 'error': 'No tienes permiso para cobrar como cortesía.'})
                messages.error(request, 'No tienes permiso para cobrar como cortesía.')
                return redirect('detalle_pedido', pedido_id=pedido_id)

        # Calcular saldo pendiente real (total de la mesa menos lo ya pagado)
        saldo_pendiente = pedido.falta_por_cobrar

        if monto_pago <= 0 or monto_pago > saldo_pendiente:
            if es_ajax:
                return JsonResponse({'ok': False, 'error': 'Monto inválido. Saldo pendiente: $' + str(int(saldo_pendiente))})
            messages.error(request, 'Monto de pago parcial inválido.')
            return redirect('detalle_pedido', pedido_id=pedido_id)

        saldo_restante = saldo_pendiente - monto_pago

        # Crear o actualizar factura parcial
        if pedido.estado == 'parcial' and pedido.factura:
            factura = pedido.factura
            factura.total += monto_pago
            factura.valor_recibido = factura.total
            factura.saldo_pendiente = saldo_restante
            factura.save()
        else:
            ultimo_numero = Factura.objects.aggregate(maximo=Max('numero'))['maximo'] or 0
            factura = Factura.objects.create(
                numero=ultimo_numero + 1,
                pedido=pedido,
                mesa=pedido.mesa,
                mesero=pedido.mesero,
                metodo_pago=metodo_pago,
                subtotal=pedido.subtotal,
                descuento=pedido.descuento,
                total=monto_pago,
                valor_recibido=monto_pago,
                es_parcial=True,
                saldo_pendiente=saldo_restante,
            )

        Pago.objects.create(
            factura=factura,
            pedido=pedido,
            metodo=metodo_pago,
            monto=monto_pago,
            valor_recibido=monto_pago,
            usuario=request.user,
        )

        pedido.saldo_pendiente = saldo_restante
        if saldo_restante <= 0:
            # La mesa quedó pagada por completo con pagos parciales:
            # se cierra como si hubiera sido un pago normal.
            factura.es_parcial = False
            factura.saldo_pendiente = 0
            factura.save()
            pedido.estado = 'pagado'
            pedido.fecha_cierre = timezone.now()
            pedido.mesa.estado = 'libre'
        else:
            pedido.estado = 'parcial'
            pedido.mesa.estado = 'parcial'
        pedido.save()
        pedido.mesa.save()

        # Descontar inventario completo al primer pago (incluye combos)
        if not Factura.objects.filter(pedido=pedido, es_parcial=True).exclude(pk=factura.pk).exists():
            from apps.inventario.services import descontar_pedido
            descontar_pedido(pedido)

        if es_ajax:
            return JsonResponse({
                'ok': True,
                'factura_id': factura.id,
                'numero': factura.numero,
                'monto': float(monto_pago),
                'saldo': float(saldo_restante),
                'pagado': saldo_restante <= 0,
                'mesa': pedido.mesa.numero,
            })
        if saldo_restante <= 0:
            messages.success(
                request,
                f'Mesa {pedido.mesa.numero} pagada por completo con pagos parciales. '
                f'Factura #{factura.numero}.'
            )
        else:
            messages.success(
                request,
                f'Pago parcial registrado. Saldo pendiente: ${saldo_restante}'
            )
        return redirect('detalle_pedido', pedido_id=pedido_id)

    return redirect('detalle_pedido', pedido_id=pedido_id)


@login_required
def cancelar_pedido(request, pedido_id):
    """
    Cancela un pedido vacío y regresa la mesa a libre.
    Solo permite cancelar pedidos sin productos.
    """
    pedido = get_object_or_404(Pedido, pk=pedido_id)

    if pedido.detalles.exists():
        messages.error(request, 'No se puede cancelar un pedido con productos.')
        return redirect('detalle_pedido', pedido_id=pedido_id)

    v = getattr(request.user, 'vendedor', None)
    if not (request.user.is_staff or request.user.is_superuser):
        if not (v and v.puede('cancelar_pedido')):
            messages.error(request, 'No tienes permiso para cancelar pedidos.')
            return redirect('vista_mesas')
        if pedido.mesero_id != v.id and not (v and v.puede('modificar_otros_pedidos')):
            messages.error(request, 'No puedes cancelar pedidos de otros vendedores.')
            return redirect('vista_mesas')

    mesa = pedido.mesa
    pedido.delete()
    mesa.estado = 'libre'
    mesa.save()
    messages.success(request, f'Pedido cancelado. Mesa {mesa.numero} libre.')
    return redirect('vista_mesas')


@login_required
@admin_required
def liberar_mesa(request, mesa_id):
    """
    Cambia el estado de una mesa pagada/cerrada a libre.
    Solo administradores.
    """
    mesa = get_object_or_404(Mesa, pk=mesa_id, activa=True)
    if mesa.estado not in ('pagada', 'cerrada'):
        messages.warning(request, 'Solo se pueden liberar mesas pagadas o cerradas.')
        return redirect('vista_mesas')
    mesa.estado = 'libre'
    mesa.save()
    messages.success(request, f'Mesa {mesa.numero} liberada.')
    return redirect('vista_mesas')


@login_required
@permiso_required('facturar')
def solicitar_en_caja(request, pedido_id):
    """
    Envía los productos aún no enviados de un pedido al receptor de pedidos.

    Crea una SolicitudPedido con los detalles que aún no han sido enviados
    (solicitud IS NULL), de modo que envíos sucesivos solo mandan lo nuevo.
    """
    pedido = get_object_or_404(Pedido, pk=pedido_id)

    if not _autorizado_pedido(request.user, pedido, 'facturar', request):
        return redirect('vista_mesas')

    if request.method == 'POST':
        # Solo se envían los productos que aún no han sido enviados
        # a caja (solicitud IS NULL) Y que fueron añadidos desde que
        # el mesero entró a la mesa (sesion_inicio). Cada "Solicitar
        # en caja" envía únicamente lo nuevo de la sesión actual.
        detalles_nuevos = pedido.detalles.filter(solicitud__isnull=True)
        if pedido.sesion_inicio:
            detalles_nuevos = detalles_nuevos.filter(
                created_at__gte=pedido.sesion_inicio
            )
        if not detalles_nuevos.exists():
            messages.warning(request, 'No hay productos nuevos por enviar a caja.')
            return redirect('detalle_pedido', pedido_id=pedido_id)

        solicitud = SolicitudPedido.objects.create(
            pedido=pedido,
            mesa=pedido.mesa,
            solicitante=request.user.vendedor,
        )
        detalles_nuevos.update(solicitud=solicitud)
        messages.success(request, 'Productos enviados a caja.')
        return redirect('detalle_pedido', pedido_id=pedido_id)

    return redirect('detalle_pedido', pedido_id=pedido_id)


@login_required
@permiso_required('facturar')
def solicitar_en_caja_con_productos(request, pedido_id):
    """
    Recibe productos seleccionados en el modal, los agrega al pedido
    y crea una SolicitudPedido para enviar a caja.
    """
    import json

    pedido = get_object_or_404(Pedido, pk=pedido_id)

    if not _autorizado_pedido(request.user, pedido, 'facturar', request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Permiso denegado'}, status=403)
        return redirect('vista_mesas')

    if pedido.estado not in ('activo', 'parcial'):
        msg = 'No se pueden agregar productos a un pedido pagado o cerrado.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': msg}, status=400)
        messages.error(request, msg)
        return redirect('detalle_pedido', pedido_id=pedido_id)

    if request.method != 'POST':
        return redirect('detalle_pedido', pedido_id=pedido_id)

    try:
        data = json.loads(request.body)
        productos = data.get('productos', [])
    except (json.JSONDecodeError, AttributeError):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Datos inválidos'}, status=400)
        return redirect('detalle_pedido', pedido_id=pedido_id)

    if not productos:
        msg = 'No se seleccionaron productos.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': msg}, status=400)
        messages.warning(request, msg)
        return redirect('detalle_pedido', pedido_id=pedido_id)

    solicitud = SolicitudPedido.objects.create(
        pedido=pedido,
        mesa=pedido.mesa,
        solicitante=request.user.vendedor,
    )

    detalles_agregados = []
    for item in productos:
        producto_id = item.get('producto_id')
        cantidad = Decimal(str(item.get('cantidad', 1)))
        cortesia = item.get('cortesia', False)
        precio_str = item.get('precio_unitario', '')
        precio_personalizado = Decimal(str(precio_str)) if precio_str else None

        cortesia_ok, precio_ok = _puede_cortesia_o_precio(
            request.user, request, cortesia, precio_personalizado is not None)
        if not cortesia_ok:
            cortesia = False
        if not precio_ok:
            precio_personalizado = None

        try:
            producto = Producto.objects.get(pk=producto_id)
        except Producto.DoesNotExist:
            continue

        if cortesia:
            precio = 0
        elif precio_personalizado is not None:
            precio = precio_personalizado
        else:
            precio = producto.precio_venta

        detalle = DetallePedido.objects.create(
            pedido=pedido,
            producto=producto,
            es_cortesia=cortesia,
            precio_unitario=precio,
            cantidad=cantidad,
            subtotal=precio * cantidad,
            solicitud=solicitud,
        )
        detalles_agregados.append(detalle)

    pedido.calcular_totales()

    if not detalles_agregados:
        solicitud.delete()
        msg = 'No se pudieron agregar los productos.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': msg}, status=400)
        messages.error(request, msg)
        return redirect('detalle_pedido', pedido_id=pedido_id)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'solicitud_id': solicitud.id,
            'total_pedido': float(pedido.total),
        })

    messages.success(request, 'Productos agregados y enviados a caja.')
    return redirect('detalle_pedido', pedido_id=pedido_id)


@login_required
def solicitudes_pendientes_api(request):
    """API que retorna las solicitudes pendientes para el receptor de pedidos."""
    v = getattr(request.user, 'vendedor', None)
    if not (request.user.is_staff or request.user.is_superuser
            or (v and v.es_receptor_pedidos)):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    solicitudes = (
        SolicitudPedido.objects
        .filter(estado='pendiente')
        .select_related('mesa', 'solicitante', 'pedido')
        .prefetch_related('detalles__producto')
        .order_by('-created_at')[:20]
    )
    data = []
    for s in solicitudes:
        items = [{
            'producto': d.producto.nombre,
            'cantidad': float(d.cantidad),
            'cortesia': d.es_cortesia,
        } for d in s.detalles.all()]
        data.append({
            'id': s.id,
            'pedido_id': s.pedido_id,
            'mesa': s.mesa.numero,
            'solicitante': str(s.solicitante) if s.solicitante else '—',
            'created_at': s.created_at.strftime('%H:%M'),
            'items': items,
        })
    return JsonResponse({'solicitudes': data})


@login_required
def marcar_solicitud_atendida(request, solicitud_id):
    """Marca una solicitud como atendida (solo receptor de pedidos)."""
    v = getattr(request.user, 'vendedor', None)
    if not (request.user.is_staff or request.user.is_superuser
            or (v and v.es_receptor_pedidos)):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'No autorizado'}, status=403)
        messages.error(request, 'No tienes permiso para realizar esta acción.')
        return redirect('vista_mesas')

    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    solicitud = get_object_or_404(SolicitudPedido, pk=solicitud_id, estado='pendiente')
    solicitud.estado = 'atendida'
    solicitud.save()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True})
    return redirect('pedidos_vendedores')


@login_required
def pedidos_vendedores(request):
    """
    Módulo "Pedidos de vendedores" para el receptor de pedidos.

    Muestra el historial de solicitudes enviadas a caja (pendientes,
    atendidas o todas) y permite marcar las pendientes como atendidas.
    """
    v = getattr(request.user, 'vendedor', None)
    if not (request.user.is_staff or request.user.is_superuser
            or (v and v.es_receptor_pedidos)):
        messages.error(request, 'No tienes acceso a este módulo.')
        return redirect('vista_mesas')

    estado = request.GET.get('estado', 'pendiente')
    solicitudes = (
        SolicitudPedido.objects
        .select_related('mesa', 'solicitante', 'pedido')
        .prefetch_related('detalles__producto')
        .order_by('-created_at')
    )
    if estado in ('pendiente', 'atendida'):
        solicitudes = solicitudes.filter(estado=estado)

    pendientes = SolicitudPedido.objects.filter(estado='pendiente').count()
    atendidas = SolicitudPedido.objects.filter(estado='atendida').count()

    return render(request, 'mesas/pedidos_vendedores.html', {
        'solicitudes': solicitudes,
        'estado': estado,
        'pendientes': pendientes,
        'atendidas': atendidas,
    })


@login_required
def cambiar_mesero(request, pedido_id):
    """
    Cambia el mesero asignado a un pedido.
    Solo administradores.
    """
    if not request.user.is_staff:
        messages.error(request, 'Permiso denegado.')
        return redirect('vista_mesas')

    pedido = get_object_or_404(Pedido, pk=pedido_id)
    if request.method == 'POST':
        mesero_id = request.POST.get('mesero_id')
        if mesero_id:
            mesero = get_object_or_404(Vendedor, pk=mesero_id)
            pedido.mesero = mesero
            pedido.save()
            messages.success(request, f'Mesero cambiado a {mesero}')

    return redirect('detalle_pedido', pedido_id=pedido_id)


@login_required
@permiso_required('trasladar_mesas')
def trasladar_pedido(request, pedido_id):
    """
    Traslada un pedido activo de una mesa a otra.
    """
    pedido = get_object_or_404(Pedido, pk=pedido_id, estado__in=['activo', 'parcial'])
    mesas_disponibles = Mesa.objects.filter(activa=True).exclude(pk=pedido.mesa_id)

    if request.method == 'POST':
        nueva_mesa_id = request.POST.get('nueva_mesa')
        if nueva_mesa_id:
            nueva_mesa = get_object_or_404(Mesa, pk=nueva_mesa_id, activa=True)
            mesa_anterior = pedido.mesa
            pedido.mesa = nueva_mesa
            pedido.save()

            mesa_anterior.estado = 'libre'
            mesa_anterior.save()

            nueva_mesa.estado = 'activo'
            nueva_mesa.save()

            messages.success(
                request,
                f'Pedido trasladado de Mesa {mesa_anterior.numero} a Mesa {nueva_mesa.numero}.'
            )
            return redirect('detalle_pedido', pedido_id=pedido_id)

    return render(request, 'mesas/trasladar_pedido.html', {
        'pedido': pedido,
        'mesas_disponibles': mesas_disponibles,
    })
