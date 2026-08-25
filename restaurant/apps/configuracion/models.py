"""
Modelos de configuración general del sistema.

Permite al administrador personalizar el nombre y el logo de la empresa,
los cuales se muestran en el navbar y en la pantalla de inicio de sesión.
"""
from django.db import models


class Configuracion(models.Model):
    """
    Configuración general de la empresa (modelo singleton).

    Solo existe un registro (pk=1). Se accede con el método de clase
    ``obtener()``, que lo crea con valores por defecto si no existe.
    """
    nombre_empresa = models.CharField(
        'Nombre de la empresa', max_length=100, default='El Choli'
    )
    logo = models.ImageField(
        'Logo', upload_to='logos/', blank=True, null=True,
        help_text='Imagen que se muestra junto al nombre en el navbar y el login.'
    )
    qr_consignacion = models.ImageField(
        'QR de consignación', upload_to='qrs/', blank=True, null=True,
        help_text='Código QR que se muestra al cobrar con transferencia para que el cliente consigne.'
    )
    nit = models.CharField('NIT', max_length=30, blank=True)
    direccion = models.CharField('Dirección', max_length=200, blank=True)
    telefono = models.CharField('Teléfono', max_length=30, blank=True)

    class Meta:
        verbose_name = 'Configuración'
        verbose_name_plural = 'Configuración'

    def __str__(self):
        return self.nombre_empresa

    @classmethod
    def obtener(cls):
        """Retorna la configuración única, creándola si no existe."""
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={'nombre_empresa': 'El Choli'},
        )
        return obj
