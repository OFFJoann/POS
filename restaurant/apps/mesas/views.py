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
from .models import Mesa, Pedido, DetallePedido
from .services import (
    crear_pedido, agregar_producto_a_pedido,
    modificar_cantidad, eliminar_detalle,
    aplicar_descuento, cerrar_pedido
)
from .forms import AgregarProductoForm, DescuentoForm, MesaForm
from apps.productos.models import Producto, Categoria
from apps.usuarios.decorators import admin_required
from apps.usuarios.models import Vendedor
from apps.ventas.models import Factura, Pago
from apps.caja.models import AperturaCaja
from apps.inventario.services import descontar_inventario


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
    categorias = Categoria.objects.filter(activo=True)
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

    # Verificar permisos
    if pedido.mesero != request.user.vendedor and not request.user.is_staff:
        messages.error(request, 'No puedes modificar pedidos de otros vendedores.')
        return redirect('vista_mesas')

    categorias = Categoria.objects.filter(activo=True)
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

    if pedido.estado != 'activo':
        messages.error(request, 'No se pueden agregar productos a un pedido pagado o en pago parcial.')
        return redirect('detalle_pedido', pedido_id=pedido_id)

    if pedido.mesero != request.user.vendedor and not request.user.is_staff:
        return JsonResponse({'error': 'Permiso denegado'}, status=403)

    if request.method == 'POST':
        producto_id = request.POST.get('producto_id')
        cantidad = Decimal(request.POST.get('cantidad', 1))
        cortesia = request.POST.get('cortesia') == 'true'
        precio_str = request.POST.get('precio_unitario', '').strip()
        precio_personalizado = Decimal(precio_str) if precio_str else None

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
        if detalle.pedido.estado != 'activo':
            messages.error(request, 'No se puede modificar un pedido pagado o en pago parcial.')
            return redirect('detalle_pedido', pedido_id=pedido_id)
        if detalle.pedido.mesero != request.user.vendedor and not request.user.is_staff:
            messages.error(request, 'Permiso denegado.')
            return redirect('vista_mesas')

        precio_unitario = request.POST.get('precio_unitario')
        if precio_unitario:
            detalle.precio_unitario = Decimal(precio_unitario)
            detalle.subtotal = detalle.cantidad * detalle.precio_unitario
            detalle.save()
            detalle.pedido.calcular_totales()
            messages.success(request, 'Precio actualizado.')
            return redirect('detalle_pedido', pedido_id=pedido_id)

        nueva_cantidad = request.POST.get('cantidad')
        if nueva_cantidad and Decimal(nueva_cantidad) > 0:
            modificar_cantidad(detalle_id, Decimal(nueva_cantidad))
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
    if not request.user.is_staff:
        messages.error(request, 'Solo administradores pueden aplicar descuentos.')
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

    if not AperturaCaja.objects.filter(activa=True).exists():
        messages.error(request, 'No se puede facturar porque la caja está cerrada.')
        return redirect('detalle_pedido', pedido_id=pedido_id)

    pedido = get_object_or_404(
        Pedido.objects.select_related('mesa', 'mesero'),
        pk=pedido_id
    )

    if request.method == 'POST':
        metodo_pago = request.POST.get('metodo_pago')
        monto_a_cobrar = pedido.saldo_pendiente if pedido.estado == 'parcial' else pedido.total
        valor_recibido = Decimal(request.POST.get('valor_recibido', 0))

        if metodo_pago not in ['efectivo', 'transferencia', 'cortesia']:
            messages.error(request, 'Método de pago inválido.')
            return redirect('detalle_pedido', pedido_id=pedido_id)

        if valor_recibido < monto_a_cobrar:
            messages.error(request, 'El valor recibido es menor al monto a cobrar.')
            return redirect('detalle_pedido', pedido_id=pedido_id)

        cambio = valor_recibido - monto_a_cobrar

        # Crear o actualizar factura
        if pedido.estado == 'parcial':
            factura = pedido.factura
            factura.metodo_pago = metodo_pago
            factura.total += monto_a_cobrar
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

            # Descontar inventario agrupando por producto (evita duplicar instancias)
            from itertools import groupby
            from operator import attrgetter
            from apps.inventario.services import descontar_inventario
            detalles = pedido.detalles.select_related('producto').order_by('producto_id').all()
            for producto_id, grupo in groupby(detalles, attrgetter('producto_id')):
                items = list(grupo)
                total_cantidad = sum(d.cantidad for d in items)
                descontar_inventario(
                    producto=items[0].producto,
                    cantidad=total_cantidad,
                    pedido_id=pedido.id,
                )

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

        pedido.mesa.estado = 'pagada'
        pedido.mesa.save()

        messages.success(
            request,
            f'Factura #{factura.numero} generada. Cambio: ${cambio}'
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

    if not AperturaCaja.objects.filter(activa=True).exists():
        messages.error(request, 'No se puede facturar porque la caja está cerrada.')
        return redirect('detalle_pedido', pedido_id=pedido_id)

    pedido = get_object_or_404(Pedido, pk=pedido_id)

    if request.method == 'POST':
        metodo_pago = request.POST.get('metodo_pago')
        monto_pago = Decimal(request.POST.get('monto_pago', 0))

        if metodo_pago not in ['efectivo', 'transferencia', 'cortesia']:
            messages.error(request, 'Método de pago inválido.')
            return redirect('detalle_pedido', pedido_id=pedido_id)

        if monto_pago <= 0 or monto_pago >= pedido.total:
            messages.error(request, 'Monto de pago parcial inválido.')
            return redirect('detalle_pedido', pedido_id=pedido_id)

        saldo_restante = pedido.total - monto_pago

        # Crear factura parcial
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
        pedido.estado = 'parcial'
        pedido.save()

        pedido.mesa.estado = 'parcial'
        pedido.mesa.save()

        # Descontar inventario completo al primer pago (agrupado por producto)
        if not Factura.objects.filter(pedido=pedido, es_parcial=True).exclude(pk=factura.pk).exists():
            from itertools import groupby
            from operator import attrgetter
            detalles = pedido.detalles.select_related('producto').order_by('producto_id').all()
            for producto_id, grupo in groupby(detalles, attrgetter('producto_id')):
                items = list(grupo)
                total_cantidad = sum(d.cantidad for d in items)
                descontar_inventario(
                    items[0].producto,
                    total_cantidad,
                    pedido_id=pedido.id,
                )

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

    if pedido.mesero != request.user.vendedor and not request.user.is_staff:
        messages.error(request, 'Permiso denegado.')
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
