"""Modelo de licencia del servidor central."""
from datetime import date
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.conf import settings


class Licencia(models.Model):
    """Licencia vendida a un cliente del POS.

    El POS consulta GET /api/licencia/?codigo=X y recibe el payload firmado.
    Para renovar solo se actualiza `fecha_vencimiento` (o se cambia
    `limite_vendedores`) desde el panel de administración; los clientes lo
    toman en su siguiente validación, sin tocar sus .env.
    """
    codigo = models.CharField(
        'Código', max_length=50, unique=True,
        help_text='Código único que el cliente pone en LICENCIA_CODIGO.')
    cliente = models.CharField('Cliente', max_length=150,
        help_text='Nombre visible del negocio licenciado.')
    fecha_inicio = models.DateField('Inicio',
        default=date.today)
    fecha_vencimiento = models.DateField('Vencimiento',
        help_text='Último día de validez (inclusive).')
    limite_vendedores = models.PositiveIntegerField(
        'Límite de vendedores', default=5,
        help_text='Máximo de vendedores activos permitidos (0 = sin límite).')
    mensualidad = models.DecimalField(
        'Mensualidad', max_digits=10, decimal_places=2,
        default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0'))],
        help_text='Lo que el cliente paga cada mes por esta licencia. '
                  'El panel suma las licencias activas para calcular el ingreso mensual.')
    features = models.JSONField(
        'Características', default=dict, blank=True,
        help_text='Extras para el futuro (descuento por módulos, etc.).')
    activa = models.BooleanField('Activa', default=True,
        help_text='Desmarcar pausa la licencia (el POS la tratará como inválida).')
    creada_en = models.DateTimeField('Creada', auto_now_add=True)
    actualizada_en = models.DateTimeField('Actualizada', auto_now=True)

    class Meta:
        verbose_name = 'Licencia'
        verbose_name_plural = 'Licencias'
        ordering = ['cliente']

    def __str__(self):
        return f'{self.codigo} · {self.cliente}'

    @property
    def dias_restantes(self):
        if not self.fecha_vencimiento:
            return None
        return (self.fecha_vencimiento - date.today()).days


class UsuarioPanel(models.Model):
    """Rol de una cuenta dentro del panel de licencias.

    La contraseña y el estado los lleva `django.contrib.auth.User`; aquí solo
    está el permiso sobre las licencias. Se usa un perfil en vez de sustituir
    `AUTH_USER_MODEL` para no tocar la tabla de usuarios ni las sesiones que
    ya hay en marcha.

    Roles:
      - Administrador: ve y modifica todo, incluido el secreto compartido.
      - Visualizador:  solo lee. El backend rechaza cualquier escritura.
    """
    ADMINISTRADOR = 'administrador'
    VISUALIZADOR = 'visualizador'
    ROLES = [
        (ADMINISTRADOR, 'Administrador'),
        (VISUALIZADOR, 'Visualizador'),
    ]

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='panel', verbose_name='Usuario')
    rol = models.CharField(
        'Rol', max_length=20, choices=ROLES, default=VISUALIZADOR)

    class Meta:
        verbose_name = 'Usuario del panel'
        verbose_name_plural = 'Usuarios del panel'
        ordering = ['usuario__username']

    def __str__(self):
        return f'{self.usuario} · {self.get_rol_display()}'

    @property
    def es_administrador(self):
        return self.rol == self.ADMINISTRADOR