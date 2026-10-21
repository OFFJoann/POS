"""
Lógica de negocio de los créditos: creación del calendario y registro de abonos.
"""
import calendar
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import models, transaction
from django.utils import timezone

from .models import Abono, Cliente, Credito, Cuota


def _obtener_cliente(nombre, correo='', cedula='', telefono=''):
    """Busca un cliente por nombre (y correo) o lo crea."""
    nombre = (nombre or '').strip()
    correo = (correo or '').strip()
    consulta = Cliente.objects.filter(nombre__iexact=nombre)
    if correo:
        consulta = consulta.filter(correo__iexact=correo)
    cliente = consulta.first()
    if cliente:
        # Completa datos que faltaban si ahora llegan.
        actualizado = False
        if correo and not cliente.correo:
            cliente.correo = correo
            actualizado = True
        if cedula and not cliente.cedula:
            cliente.cedula = cedula
            actualizado = True
        if telefono and not cliente.telefono:
            cliente.telefono = telefono
            actualizado = True
        if actualizado:
            cliente.save()
        return cliente
    return Cliente.objects.create(
        nombre=nombre, correo=correo, cedula=cedula, telefono=telefono)


def _ultimo_dia(anio, mes):
    """Último día del mes dado."""
    return date(anio, mes, calendar.monthrange(anio, mes)[1])


def _fechas_vencimiento(fecha_base, n, frecuencia):
    """Devuelve `n` fechas de vencimiento en fechas fijas de calendario.

    - 'mensual': vence el **último día de cada mes**.
    - 'quincenal': vence el **día 15 y el último día de cada mes**.

    La primera cuota cae en la próxima fecha de calendario estrictamente
    posterior a `fecha_base` (el día de la venta); luego siguen las fechas
    siguientes en orden.
    """
    fechas = []
    anio, mes = fecha_base.year, fecha_base.month
    while len(fechas) < n:
        if frecuencia == 'quincenal':
            candidatas = [date(anio, mes, 15), _ultimo_dia(anio, mes)]
        else:
            candidatas = [_ultimo_dia(anio, mes)]
        for f in candidatas:
            if f > fecha_base and len(fechas) < n:
                fechas.append(f)
        mes += 1
        if mes > 12:
            mes = 1
            anio += 1
    return fechas


@transaction.atomic
def crear_credito(factura, nombre_cliente, num_cuotas, correo='', cedula='',
                  telefono='', observaciones='', monto=None, frecuencia='mensual'):
    """Crea el crédito (y su calendario de cuotas) para una factura.

    El total se divide en `num_cuotas` iguales sin interés; el redondeo de los
    centavos va en la última cuota para que la suma cuadre exacta.

    `monto` permite financiar solo una parte (p. ej. el saldo restante de una
    factura que ya tuvo pagos parciales). Por defecto financia `factura.total`.

    `frecuencia` define el calendario: 'mensual' (último día de cada mes) o
    'quincenal' (día 15 y último día de cada mes).
    """
    num_cuotas = max(1, int(num_cuotas))
    total = Decimal(monto if monto is not None else factura.total)
    if frecuencia not in ('mensual', 'quincenal'):
        frecuencia = 'mensual'
    cliente = _obtener_cliente(nombre_cliente, correo, cedula, telefono)

    credito = Credito.objects.create(
        factura=factura,
        cliente=cliente,
        cuotas_total=num_cuotas,
        frecuencia=frecuencia,
        monto_total=total,
        saldo_pendiente=total,
        observaciones=(observaciones or '').strip(),
    )

    base = (total / num_cuotas).quantize(Decimal('0.01'), ROUND_HALF_UP)
    fecha_base = timezone.localdate()
    vencimientos = _fechas_vencimiento(fecha_base, num_cuotas, frecuencia)
    acumulado = Decimal('0')
    for i in range(1, num_cuotas + 1):
        monto_cuota = base if i < num_cuotas else (total - acumulado)
        acumulado += monto_cuota
        Cuota.objects.create(
            credito=credito,
            numero=i,
            fecha_vencimiento=vencimientos[i - 1],
            monto=monto_cuota,
        )
    return credito


@transaction.atomic
def crear_credito_preexistente(nombre_cliente, monto, correo='', cedula='',
                               telefono='', observaciones='', usuario=None):
    """Registra un crédito ya existente que no nació de una venta del sistema.

    Se usa para anotar deudas antiguas que aún no estaban en el sistema. No
    crea Factura ni calendario de cuotas: solo el saldo a cobrar. A diferencia
    de un crédito normal, los abonos que el cliente vaya haciendo Sí cuentan
    como ventas del día (ver `registrar_abono`).
    """
    monto = Decimal(str(monto))
    if monto <= 0:
        raise ValueError('El monto del crédito debe ser mayor a cero.')
    nombre_cliente = (nombre_cliente or '').strip()
    if not nombre_cliente:
        raise ValueError('Debes indicar el nombre del cliente.')

    cliente = _obtener_cliente(nombre_cliente, correo, cedula, telefono)
    return Credito.objects.create(
        factura=None,
        cliente=cliente,
        cuotas_total=0,
        frecuencia='mensual',
        monto_total=monto,
        saldo_pendiente=monto,
        es_preexistente=True,
        observaciones=(observaciones or '').strip(),
    )


# ─── Abonos ──────────────────────────────────────────────────────────────────

def _puesto_credito():
    """Puesto virtual usado para facturar los abonos de créditos anotados.

    Crea (si no existe) una Mesa tipo caja fuera de la numeración normal, para
    que los abonos aparezcan como facturas de caja sin mezclarse con las mesas.
    """
    from apps.mesas.models import Mesa
    puesto, _ = Mesa.objects.get_or_create(
        tipo='caja', numero=9999,
        defaults={'estado': 'libre', 'activa': False},
    )
    return puesto


def _mesero_para_abono(usuario):
    """Vendedor con el que se firma la factura de un abono."""
    from apps.usuarios.models import Vendedor
    vendedor = getattr(usuario, 'vendedor', None)
    if vendedor is not None:
        return vendedor
    return Vendedor.objects.filter(activo=True).first() or Vendedor.objects.first()


@transaction.atomic
def _facturar_abono_preexistente(credito, monto, metodo, usuario, observacion=''):
    """Registra el abono como una factura+pago para que sume al cierre de caja.

    Devuelve la Factura creada (o None si no se pudo: sin vendedor). Se usa una
    factura "de un solo renglón" con el monto del abono; el pedido no lleva
    productos porque no corresponde a una venta de artículos.
    """
    from apps.mesas.models import Pedido
    from apps.ventas.models import Factura, Pago
    from django.db.models import Max

    mesero = _mesero_para_abono(usuario)
    if mesero is None:
        return None

    puesto = _puesto_credito()
    pedido = Pedido.objects.create(
        mesa=puesto,
        mesero=mesero,
        subtotal=monto,
        total=monto,
        saldo_pendiente=0,
        estado='pagado',
        fecha_cierre=timezone.now(),
    )

    ultimo_numero = Factura.objects.aggregate(maximo=Max('numero'))['maximo'] or 0
    factura = Factura(
        numero=ultimo_numero + 1,
        pedido=pedido,
        mesa=puesto,
        mesero=mesero,
        metodo_pago=metodo,
        subtotal=monto,
        descuento=Decimal('0'),
        total=monto,
        valor_recibido=monto,
        cambio=Decimal('0'),
    )
    factura._skip_inventory_deduction = True
    factura.save()

    Pago.objects.create(
        factura=factura,
        pedido=pedido,
        metodo=metodo,
        monto=monto,
        valor_recibido=monto,
        cambio=Decimal('0'),
        usuario=usuario,
    )
    return factura


def _actualizar_factura_abono(abono, nuevo_monto):
    """Sincroniza la Factura/Pago de un abono anotado con su nuevo monto.

    Solo tiene efecto si el abono generó una factura (crédito anotado). Los
    montos de caja deben cuadrar con el abono vigente.
    """
    from apps.ventas.models import Pago
    factura = abono.factura
    if factura is None:
        return
    factura.subtotal = nuevo_monto
    factura.total = nuevo_monto
    factura.valor_recibido = nuevo_monto
    factura.save(update_fields=['subtotal', 'total', 'valor_recibido'])
    Pago.objects.filter(factura=factura).update(
        monto=nuevo_monto, valor_recibido=nuevo_monto)
    # El pedido asociado también debe reflejar el monto.
    from apps.mesas.models import Pedido
    Pedido.objects.filter(pk=factura.pedido_id).update(
        subtotal=nuevo_monto, total=nuevo_monto)


def caja_abierta():
    """Devuelve la AperturaCaja activa o None."""
    from apps.caja.models import AperturaCaja
    return AperturaCaja.objects.filter(activa=True).first()


def abono_editable(abono):
    """True si el abono cae dentro de la ventana de la caja abierta actual.

    Solo se pueden modificar abonos registrados durante la caja que sigue
    abierta: si esa caja ya cerró, el abono queda bloqueado.
    """
    caja = caja_abierta()
    if caja is None:
        return False
    return caja.fecha_apertura <= abono.creado_en


@transaction.atomic
def registrar_abono(credito, monto, metodo='efectivo', usuario=None,
                    cuota_id=None, observacion=''):
    """Registra un abono y lo aplica a las cuotas abiertas más antiguas.

    Un abono puede dejar una cuota 'parcial' si no alcanza a cubrirla
    completa; en ese caso se acumula en `Cuota.monto_pagado` y la cuota se
    etiqueta como parcial hasta que se complete.

    En créditos anotados (`es_preexistente`), además del Abono se genera una
    factura y un pago para que el dinero cuente como venta del día en caja.

    Exige que haya una caja abierta. Devuelve el Abono creado. Lanza
    ValueError si el monto es inválido o si la caja está cerrada.
    """
    caja = caja_abierta()
    if caja is None:
        raise ValueError('No se puede abonar porque la caja está cerrada.')

    monto = Decimal(monto)
    if monto <= 0:
        raise ValueError('El monto del abono debe ser mayor a cero.')
    if monto > credito.saldo_pendiente:
        raise ValueError('El abono supera el saldo pendiente del crédito.')

    if metodo not in ('efectivo', 'transferencia'):
        metodo = 'efectivo'

    cuota_preferida = None
    if cuota_id:
        cuota_preferida = credito.cuotas.filter(pk=cuota_id).first()

    abono = Abono.objects.create(
        credito=credito,
        monto=monto,
        metodo=metodo,
        usuario=usuario,
        cuota=cuota_preferida,
        observacion=(observacion or '').strip(),
        es_preexistente=credito.es_preexistente,
    )

    # Crédito anotado: el dinero debe entrar a la caja del día.
    if credito.es_preexistente:
        factura = _facturar_abono_preexistente(
            credito, monto, metodo, usuario, observacion=observacion)
        if factura is not None:
            abono.factura = factura
            abono.save(update_fields=['factura'])

    recalcular_cuotas(credito)
    _recalcular_saldo(credito)
    return abono


def _recalcular_saldo(credito):
    """Saldo = monto total menos la suma de todos los abonos vigentes."""
    total_abonado = credito.abonos.aggregate(
        total=models.Sum('monto'))['total'] or Decimal('0')
    saldo = credito.monto_total - total_abonado
    credito.saldo_pendiente = saldo if saldo > 0 else Decimal('0')
    credito.save(update_fields=['saldo_pendiente'])
    credito.recalcular_estado()
    return credito.saldo_pendiente


def recalcular_cuotas(credito):
    """Reconstruye el calendario aplicando los abonos en orden cronológico.

    Deja cada cuota en 'pendiente', 'parcial' o 'pagada' según la suma de
    abonos. Respeta la cuota preferida de cada abono (si se indicó al
    registrarlo). Sirve tanto al registrar como al editar abonos.
    """
    cuotas = list(credito.cuotas.order_by('numero'))
    if not cuotas:
        return
    for cuota in cuotas:
        cuota.monto_pagado = Decimal('0')
        cuota.estado = 'pendiente'
        cuota.fecha_pago = None

    abonos = credito.abonos.order_by('creado_en', 'pk')
    for abono in abonos:
        restante = abono.monto
        if restante <= 0:
            continue
        if abono.cuota_id:
            ordenadas = ([c for c in cuotas if c.pk == abono.cuota_id]
                         + [c for c in cuotas if c.pk != abono.cuota_id])
        else:
            ordenadas = cuotas
        for cuota in ordenadas:
            if restante <= 0:
                break
            falta = cuota.monto - cuota.monto_pagado
            if falta <= 0:
                continue
            a_pagar = falta if restante >= falta else restante
            cuota.monto_pagado += a_pagar
            restante -= a_pagar
            cuota.estado = ('pagada'
                            if cuota.monto_pagado >= cuota.monto else 'parcial')
            if cuota.estado == 'pagada' and cuota.fecha_pago is None:
                cuota.fecha_pago = timezone.localdate()

    for cuota in cuotas:
        cuota.save(update_fields=['monto_pagado', 'estado', 'fecha_pago'])


@transaction.atomic
def editar_abono(abono, nuevo_monto, usuario=None, metodo=None, observacion=None,
                 forzar=False):
    """Cambia el monto (y opcionalmente método/nota) de un abono existente.

    Por defecto solo se permite mientras el abono pertenezca a la caja que
    sigue abierta: una vez cerrada esa caja, el abono queda bloqueado. Los
    administradores pasan `forzar=True` para editar abonos ya consolidados,
    y en ese caso se recalcula el snapshot del cierre afectado. Recalcula
    cuotas y saldo, y sincroniza la factura/pago de los créditos anotados.

    Devuelve el Abono actualizado. Lanza ValueError si no se puede editar.
    """
    if not forzar and not abono_editable(abono):
        caja = caja_abierta()
        if caja is None:
            raise ValueError(
                'No se puede modificar el abono porque la caja está cerrada.')
        raise ValueError(
            'Solo se pueden modificar abonos registrados durante la caja '
            'abierta actual.')

    nuevo_monto = Decimal(nuevo_monto)
    if nuevo_monto <= 0:
        raise ValueError('El monto del abono debe ser mayor a cero.')

    credito = abono.credito
    otros = credito.abonos.exclude(pk=abono.pk).aggregate(
        total=models.Sum('monto'))['total'] or Decimal('0')
    if otros + nuevo_monto > credito.monto_total:
        raise ValueError('El abono supera el saldo pendiente del crédito.')

    if metodo is not None and metodo in ('efectivo', 'transferencia'):
        abono.metodo = metodo
    if observacion is not None:
        abono.observacion = observacion.strip()

    abono.monto = nuevo_monto
    abono.usuario = usuario or abono.usuario
    abono.save(update_fields=['monto', 'metodo', 'observacion', 'usuario'])

    _actualizar_factura_abono(abono, nuevo_monto)
    recalcular_cuotas(credito)
    _recalcular_saldo(credito)
    if forzar and abono.factura_id:
        from apps.ventas.services import recalcular_cierre_de_factura
        recalcular_cierre_de_factura(abono.factura)
    return abono


# ─── Recordatorios de cuota ──────────────────────────────────────────────────

def _fmt(valor):
    """Formatea un monto como miles con punto (ej. 150.000)."""
    try:
        return '{:,.0f}'.format(float(valor)).replace(',', '.')
    except (TypeError, ValueError):
        return str(valor)


def cuotas_para_recordatorio():
    """Cuotas que deben recibir recordatorio hoy.

    Devuelve dos querysets:
    - 'antes':   vencen mañana y aún no se avisó (recordatorio previo).
    - 'vence':   vencen hoy y aún no se avisó (aviso del día).
    Solo incluye cuotas abiertas (pendientes o parciales) con correo.
    """
    hoy = timezone.localdate()
    manana = hoy + timedelta(days=1)
    abiertas = Cuota.objects.filter(estado__in=['pendiente', 'parcial'])
    return {
        'antes': abiertas.filter(
            fecha_vencimiento=manana, aviso_antes_enviado=False,
            credito__cliente__correo__isnull=False,
        ).exclude(credito__cliente__correo=''),
        'vence': abiertas.filter(
            fecha_vencimiento=hoy, aviso_vencimiento_enviado=False,
            credito__cliente__correo__isnull=False,
        ).exclude(credito__cliente__correo=''),
    }


def enviar_recordatorio_cuota(cuota, tipo='antes'):
    """Envía un correo recordando una cuota del crédito.

    `tipo` es 'antes' (un día antes) o 'vence' (el día del vencimiento).
    Marca el aviso como enviado para no repetirlo. Retorna (ok, detalle).
    Nunca lanza excepciones.
    """
    from django.core.mail import EmailMessage
    from apps.configuracion.models import Configuracion

    cliente = cuota.credito.cliente
    correo = (cliente.correo or '').strip()
    if not correo:
        return False, 'El cliente no tiene correo registrado.'

    config = Configuracion.obtener()
    empresa = config.nombre_empresa or 'El Choli'
    fecha = cuota.fecha_vencimiento
    fecha_txt = fecha.strftime('%d/%m/%Y')

    if tipo == 'vence':
        asunto = 'Recordatorio: tu cuota vence hoy - %s' % empresa
        intro = 'Te recordamos que hoy vence tu cuota.'
    elif tipo == 'manual':
        asunto = 'Recordatorio de cuota - %s' % empresa
        intro = 'Te recordamos que tienes una cuota por pagar de tu crédito.'
    else:
        asunto = 'Recordatorio: tu cuota vence mañana - %s' % empresa
        intro = 'Te recordamos que mañana vence tu cuota.'

    cuerpo = (
        'Hola {nombre},\n\n'
        '{intro}\n\n'
        'Crédito de la factura #{factura}\n'
        'Cuota: {numero} de {total}\n'
        'Monto a pagar: ${monto}\n'
        'Vence: {fecha}\n'
        'Saldo pendiente del crédito: ${saldo}\n\n'
        'Si ya pagaste, puedes ignorar este mensaje.\n\n'
        'Gracias por su preferencia.\n'
        '{empresa}'
    ).format(
        nombre=cliente.nombre,
        intro=intro,
        factura=cuota.credito.factura.numero,
        numero=cuota.numero,
        total=cuota.credito.cuotas_total,
        monto=_fmt(cuota.monto_faltante),
        fecha=fecha_txt,
        saldo=_fmt(cuota.credito.saldo_pendiente),
        empresa=empresa,
    )

    try:
        email = EmailMessage(subject=asunto, body=cuerpo, to=[correo])
        email.send()
    except Exception as exc:
        return False, str(exc)

    if tipo == 'vence':
        cuota.aviso_vencimiento_enviado = True
        cuota.save(update_fields=['aviso_vencimiento_enviado'])
    elif tipo == 'antes':
        cuota.aviso_antes_enviado = True
        cuota.save(update_fields=['aviso_antes_enviado'])
    # 'manual' no marca ningún aviso: el envío automático puede seguir
    # enviando el suyo (antes/vence) cuando le toque.
    return True, correo


def enviar_recordatorio_credito(credito, tipo='manual'):
    """Envía un correo recordando el saldo de un crédito sin cuotas.

    Pensado para créditos preexistentes (anotados), que no tienen cuotas
    ni fechas de vencimiento. Recuerda el saldo pendiente total.
    Retorna (ok, detalle). Nunca lanza excepciones.
    """
    from django.core.mail import EmailMessage
    from apps.configuracion.models import Configuracion

    cliente = credito.cliente
    correo = (cliente.correo or '').strip()
    if not correo:
        return False, 'El cliente no tiene correo registrado.'

    config = Configuracion.obtener()
    empresa = config.nombre_empresa or 'El Choli'

    asunto = 'Recordatorio de pago - %s' % empresa
    cuerpo = (
        'Hola {nombre},\n\n'
        'Te recordamos que tienes un saldo pendiente con nosotros.\n\n'
        'Saldo pendiente: ${saldo}\n'
        'Monto original: ${monto}\n'
        'Abonado hasta ahora: ${abonado}\n\n'
        'Si ya pagaste, puedes ignorar este mensaje.\n\n'
        'Gracias por su preferencia.\n'
        '{empresa}'
    ).format(
        nombre=cliente.nombre,
        saldo=_fmt(credito.saldo_pendiente),
        monto=_fmt(credito.monto_total),
        abonado=_fmt(credito.monto_pagado),
        empresa=empresa,
    )

    try:
        email = EmailMessage(subject=asunto, body=cuerpo, to=[correo])
        email.send()
    except Exception as exc:
        return False, str(exc)

    return True, correo
