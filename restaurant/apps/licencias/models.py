"""Caché local de la última validación de licencia.

Guardamos el payload firmado que devuelve el servidor central. Con él el
sistema puede seguir funcionando sin conexión (hasta que la licencia vence
y se agota el período de gracia).
"""
from django.db import models


class EstadoLicencia(models.Model):
    """Única fila con la última respuesta válida del servidor de licencias."""
    id = models.PositiveIntegerField(
        primary_key=True, default=1, editable=False,
        help_text='Siempre es 1: solo existe una fila.')
    codigo = models.CharField('Código', max_length=50, blank=True, default='')
    cliente = models.CharField('Cliente', max_length=150, blank=True, default='')
    vigencia_hasta = models.DateField('Vigencia hasta', null=True, blank=True)
    limite_vendedores = models.PositiveIntegerField(
        'Límite de vendedores', null=True, blank=True)
    features = models.JSONField('Características', default=dict, blank=True)
    datos = models.JSONField('Payload', default=dict, blank=True)
    firma = models.CharField('Firma HMAC', max_length=128, blank=True, default='')
    actualizada_en = models.DateTimeField('Última validación', null=True, blank=True)

    class Meta:
        verbose_name = 'Estado de licencia'
        verbose_name_plural = 'Estado de licencia'

    def __str__(self):
        if not self.codigo:
            return 'Sin licencia'
        return f'{self.codigo} — válida hasta {self.vigencia_hasta or "?"}'

    @classmethod
    def obtener(cls):
        return cls.objects.filter(pk=1).first()