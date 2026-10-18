"""
Lógica de negocio de los créditos: creación del calendario y registro de abonos.
"""
import calendar
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
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
def registrar_abono(credito, monto, metodo='efectivo', usuario=None,
                    cuota_id=None, observacion=''):
    """Registra un abono y lo aplica a las cuotas abiertas más antiguas.

    Un abono puede dejar una cuota 'parcial' si no alcanza a cubrirla
    completa; en ese caso se acumula en `Cuota.monto_pagado` y la cuota se
    etiqueta como parcial hasta que se complete.

    Devuelve el Abono creado. Lanza ValueError si el monto es inválido.
    """
    monto = Decimal(monto)
    if monto <= 0:
        raise ValueError('El monto del abono debe ser mayor a cero.')
    if monto > credito.saldo_pendiente:
        raise ValueError('El abono supera el saldo pendiente del crédito.')

    abono = Abono.objects.create(
        credito=credito,
        monto=monto,
        metodo=metodo,
        usuario=usuario,
        observacion=(observacion or '').strip(),
    )

    # Cuotas abiertas (pendientes o parciales), de la más antigua a la más
    # reciente. Si se indicó una cuota concreta, se aplica primero a esa.
    abiertas = credito.cuotas.exclude(estado='pagada').order_by('numero')
    if cuota_id:
        elegida = abiertas.filter(pk=cuota_id).first()
        if elegida:
            abiertas = [elegida] + [c for c in abiertas if c.pk != elegida.pk]
        else:
            abiertas = list(abiertas)
    else:
        abiertas = list(abiertas)

    restante = monto
    for cuota in abiertas:
        if restante <= 0:
            break
        falta = cuota.monto_faltante
        if falta <= 0:
            continue
        a_pagar = falta if restante >= falta else restante
        cuota.monto_pagado += a_pagar
        restante -= a_pagar
        if cuota.monto_pagado >= cuota.monto:
            cuota.estado = 'pagada'
            cuota.fecha_pago = timezone.localdate()
            cuota.save(update_fields=['monto_pagado', 'estado', 'fecha_pago'])
        else:
            cuota.estado = 'parcial'
            cuota.save(update_fields=['monto_pagado', 'estado'])
        if abono.cuota_id is None:
            abono.cuota = cuota
            abono.save(update_fields=['cuota'])

    credito.saldo_pendiente = credito.saldo_pendiente - monto
    if credito.saldo_pendiente < 0:
        credito.saldo_pendiente = Decimal('0')
    credito.save(update_fields=['saldo_pendiente'])
    credito.recalcular_estado()
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
    """Envía el correo de recordatorio de una cuota.

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
