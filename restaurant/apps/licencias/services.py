"""Validación local de la licencia contra el servidor central.

Flujo:
  1. Si la caché es reciente (< LICENCIA_REVALIDACION_HORAS) se usa la caché.
  2. Si no, se consulta el servidor central (GET {LICENCIA_API_URL}?codigo=X).
  3. La respuesta firmada se valida (HMAC-SHA256 con LICENCIA_SECRETO) y se
     guarda como caché.
  4. Si el servidor no responde, se usa la última validación guardada.
     Cuando esa validación vence y se agota el período de gracia, se bloquea.

Valores por defecto: revalidación cada 5 h, aviso a 2 días, gracia 2 días.

Estados posibles: activa, proxima_vencer, vencida_en_gracia, bloqueada,
invalida, sin_licencia, sin_validar.
"""
import hashlib
import hmac
import json
import logging
from datetime import date, datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone

from .models import EstadoLicencia

logger = logging.getLogger(__name__)

GRACIA_DIAS = getattr(settings, 'LICENCIA_GRACIA_DIAS', 2)
REVALIDACION = timedelta(hours=getattr(settings, 'LICENCIA_REVALIDACION_HORAS', 5))
DIAS_AVISO = getattr(settings, 'LICENCIA_DIAS_AVISO', 2)

# estado -> (color bootstrap, mensaje para el banner)
BANNERS = {
    'activa': ('success', 'Licencia activa.'),
    'proxima_vencer': (
        'warning',
        'La licencia vence pronto. Contacta al proveedor para renovarla.'),
    'vencida_en_gracia': (
        'warning',
        'La licencia venció. Estás en período de gracia; renueva ya.'),
    'bloqueada': (
        'danger',
        'La licencia venció. El sistema está bloqueado hasta que se renueve.'),
    'invalida': (
        'danger',
        'La licencia no es válida. Contacta al proveedor.'),
    'sin_licencia': (
        'danger',
        'Este sistema no tiene una licencia configurada. Contacta al proveedor.'),
    'sin_validar': (
        'warning',
        'No se pudo validar la licencia con el servidor.'),
}


def _secreto():
    return (getattr(settings, 'LICENCIA_SECRETO', '') or '').strip()


def _firma_esperada(payload):
    """Reproduce el mensaje canónico firmado por el servidor."""
    base = '|'.join([
        str(payload.get('codigo', '')),
        str(payload.get('cliente', '')),
        str(payload.get('vigencia_hasta', '')),
        str(payload.get('limite_vendedores', '')),
        str(payload.get('emitido_en', '')),
    ])
    return hmac.new(_secreto().encode(), base.encode(), hashlib.sha256).hexdigest()


def _payload_valido(payload):
    """Valida estructura y firma (si hay secreto configurado en el .env)."""
    if not isinstance(payload, dict):
        return False
    for campo in ('codigo', 'cliente', 'vigencia_hasta', 'limite_vendedores',
                  'emitido_en'):
        if campo not in payload:
            return False
    try:
        date.fromisoformat(str(payload['vigencia_hasta']))
    except ValueError:
        return False
    firma = str(payload.get('firma', ''))
    if _secreto():
        if not firma:
            return False
        if not hmac.compare_digest(firma, _firma_esperada(payload)):
            return False
    return True


def _consultar_api(codigo):
    """Consulta el servidor central. Devuelve el payload o None."""
    url = (getattr(settings, 'LICENCIA_API_URL', '') or '').strip().rstrip('/')
    if not url:
        return None
    separador = '&' if '?' in url else '?'
    request = Request(
        f'{url}{separador}codigo={codigo}',
        headers={'Accept': 'application/json'},
    )
    try:
        with urlopen(request, timeout=5) as respuesta:
            datos = json.load(respuesta)
    except (URLError, HTTPError, TimeoutError, OSError, ValueError) as exc:
        logger.warning('No se pudo consultar la licencia: %s', exc)
        return None
    if not isinstance(datos, dict) or not datos.get('ok'):
        return None
    return datos.get('licencia')


def _guardar_cache(codigo, payload, ahora):
    cache = EstadoLicencia.objects.filter(pk=1).first()
    if cache is None:
        cache = EstadoLicencia(pk=1)
    cache.codigo = codigo
    cache.cliente = str(payload.get('cliente', ''))
    cache.vigencia_hasta = date.fromisoformat(str(payload['vigencia_hasta']))
    cache.limite_vendedores = int(payload.get('limite_vendedores') or 0)
    cache.features = payload.get('features') or {}
    cache.datos = payload
    cache.firma = str(payload.get('firma', ''))
    cache.actualizada_en = ahora
    cache.save()


def _datos_desde_cache(cache):
    """Payload mínimo reconstruido para cachés antiguas sin `datos`."""
    return {
        'codigo': cache.codigo,
        'cliente': cache.cliente or cache.codigo,
        'vigencia_hasta': cache.vigencia_hasta.isoformat(),
        'limite_vendedores': cache.limite_vendedores or 0,
        'emitido_en': cache.actualizada_en.isoformat() if cache.actualizada_en else '',
        'features': cache.features or {},
        'firma': cache.firma,
    }


def _estado_desde(payload, ahora):
    """Calcula el estado a partir del payload y el momento actual.

    La licencia vence el mismo día de `vigencia_hasta` (inclusive); el período
    de gracia empieza al día siguiente.
    """
    vig_date = date.fromisoformat(str(payload['vigencia_hasta']))
    vigencia = timezone.make_aware(
        datetime.combine(vig_date, datetime.max.time()))
    dias = (vig_date - timezone.localdate()).days
    if ahora > vigencia + timedelta(days=GRACIA_DIAS):
        return 'bloqueada', vigencia, dias
    if ahora > vigencia:
        return 'vencida_en_gracia', vigencia, dias
    if dias <= DIAS_AVISO:
        return 'proxima_vencer', vigencia, dias
    return 'activa', vigencia, dias


def _debe_bloquear(estado):
    """En producción (DEBUG=False) los estados críticos bloquean. En desarrollo
    solo se avisa en el banner, para no entorpecer el trabajo local."""
    if settings.DEBUG:
        return False
    return estado in ('bloqueada', 'invalida', 'sin_licencia')


def _info(estado, motivo='ok', payload=None, vigencia=None, dias=None):
    color, mensaje = BANNERS.get(estado, BANNERS['sin_validar'])
    base = {
        'estado': estado,
        'color': color,
        'mensaje': mensaje,
        'motivo': motivo,
        'codigo': '',
        'cliente': '',
        'vigencia_hasta': vigencia,
        'limite_vendedores': None,
        'dias_restantes': dias,
        'bloqueado': _debe_bloquear(estado),
    }
    if payload:
        base.update({
            'codigo': payload.get('codigo', ''),
            'cliente': payload.get('cliente', ''),
            'vigencia_hasta': vigencia,
            'limite_vendedores': payload.get('limite_vendedores'),
            'dias_restantes': dias,
        })
    return base


def obtener_licencia(force=False):
    """Devuelve el estado actual de la licencia como dict.

    Con force=True se omite la caché y se consulta el servidor.
    """
    codigo = (getattr(settings, 'LICENCIA_CODIGO', '') or '').strip()
    ahora = timezone.now()
    cache = EstadoLicencia.obtener()

    if not codigo:
        return _info('sin_licencia', motivo='sin_codigo')

    # Caché reciente válida.
    if (cache and cache.codigo == codigo and cache.actualizada_en and not force
            and (ahora - cache.actualizada_en) < REVALIDACION):
        payload = cache.datos or _datos_desde_cache(cache)
        estado, vigencia, dias = _estado_desde(payload, ahora)
        return _info(estado, motivo='cache', payload=payload,
                     vigencia=vigencia, dias=dias)

    # Consulta al servidor.
    payload = _consultar_api(codigo)
    if payload and _payload_valido(payload):
        _guardar_cache(codigo, payload, ahora)
        estado, vigencia, dias = _estado_desde(payload, ahora)
        return _info(estado, motivo='ok', payload=payload,
                     vigencia=vigencia, dias=dias)
    if payload is not None:
        # El servidor respondió pero la firma/esquema no cuadran.
        return _info('invalida', motivo='firma_invalida', payload=payload)

    # Sin respuesta: usar la última validación guardada.
    if cache and cache.codigo == codigo and cache.vigencia_hasta:
        payload = cache.datos or _datos_desde_cache(cache)
        estado, vigencia, dias = _estado_desde(payload, ahora)
        return _info(estado, motivo='offline', payload=payload,
                     vigencia=vigencia, dias=dias)

    return _info('sin_validar', motivo='sin_respuesta')