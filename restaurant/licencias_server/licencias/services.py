"""Emisión y firma de tokens de licencia (servidor central)."""
import hashlib
import hmac
from datetime import datetime, timezone

from django.conf import settings


def _firma(mensaje):
    """HMAC-SHA256 del mensaje canónico con el secreto compartido."""
    secreto = (getattr(settings, 'LICENCIA_SECRETO', '') or '').encode()
    return hmac.new(secreto, mensaje.encode(), hashlib.sha256).hexdigest()


def construir_payload(licencia):
    """Construye el payload firmado que consume el POS.

    El mensaje firmado es ``codigo|cliente|vigencia_hasta|limite_vendedores|emitido_en``.
    El cliente reproduce el mismo mensaje y compara la firma con
    ``hmac.compare_digest``; cualquier token manipulado o ajeno al secreto
    compartido queda descartado.
    """
    emitido_en = datetime.now(timezone.utc).isoformat()
    base = '|'.join([
        licencia.codigo,
        licencia.cliente,
        licencia.fecha_vencimiento.isoformat(),
        str(licencia.limite_vendedores),
        emitido_en,
    ])
    return {
        'codigo': licencia.codigo,
        'cliente': licencia.cliente,
        'vigencia_hasta': licencia.fecha_vencimiento.isoformat(),
        'limite_vendedores': licencia.limite_vendedores,
        'features': licencia.features,
        'emitido_en': emitido_en,
        'firma': _firma(base),
    }