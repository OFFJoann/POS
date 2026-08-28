"""
Modelos de la aplicación usuarios.

Define el perfil de vendedor con autenticación por cédula.
"""
from django.db import models
from django.contrib.auth.models import User


class Vendedor(models.Model):
    """
    Perfil de vendedor de El Choli.

    La cédula es el identificador único para iniciar sesión.
    No se requiere contraseña.
    """
    usuario = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='vendedor',
        verbose_name='Usuario Django'
    )
    nombre = models.CharField('Nombre', max_length=100)
    apellidos = models.CharField('Apellidos', max_length=100)
    cedula = models.CharField(
        'Cédula', max_length=20, unique=True,
        db_index=True,
        help_text='Identificador único para iniciar sesión'
    )
    telefono = models.CharField('Teléfono', max_length=20, blank=True)
    activo = models.BooleanField('Activo', default=True)

    # ─── Permisos granulares por vendedor ────────────────────────────────────
    # El administrador (usuario is_staff/is_superuser) siempre tiene todos los
    # permisos. Para vendedores no administradores, cada acción se controla
    # con estos booleanos.
    perm_facturar = models.BooleanField('Facturar y cobrar', default=True,
        help_text='Abrir pedidos, agregar productos y cobrar ventas.')
    perm_cambiar_precio = models.BooleanField('Cambiar precios', default=False,
        help_text='Modificar el precio de los productos al vender.')
    perm_cortesia = models.BooleanField('Dar cortesías', default=False,
        help_text='Marcar productos o ventas completas como cortesía (gratis).')
    perm_descuento = models.BooleanField('Aplicar descuentos', default=False,
        help_text='Aplicar descuentos manuales al pedido.')
    perm_trasladar_mesas = models.BooleanField('Trasladar mesas', default=False,
        help_text='Mover pedidos de una mesa a otra.')
    perm_cancelar_pedido = models.BooleanField('Cancelar pedidos', default=False,
        help_text='Cancelar pedidos abiertos.')
    perm_productos = models.BooleanField('Gestionar productos', default=False,
        help_text='Crear, editar y eliminar productos, categorías y unidades.')
    perm_inventario = models.BooleanField('Gestionar inventario', default=False,
        help_text='Registrar movimientos y consumo interno.')
    perm_reportes = models.BooleanField('Ver reportes', default=False,
        help_text='Acceder a reportes y exportaciones.')
    perm_caja = models.BooleanField('Caja', default=False,
        help_text='Apertura, cierre y egresos de caja.')
    perm_modificar_otros_pedidos = models.BooleanField(
        'Modificar mesas de otros', default=False,
        help_text='Permite operar mesas/pedidos de otros vendedores. '
                  'Sin este permiso, cada vendedor solo maneja sus propias mesas.')
    perm_configuracion = models.BooleanField('Configuración', default=False,
        help_text='Editar la configuración del sistema.')
    perm_ver_totales_caja = models.BooleanField('Ver totales de caja', default=False,
        help_text='Ver el dinero esperado y los totales al cerrar la caja. '
                  'Sin este permiso, puede cerrar la caja pero no verá los montos.')
    perm_ver_facturas = models.BooleanField('Ver facturas', default=True,
        help_text='Consultar y ver el detalle de las facturas emitidas. '
                  'Independiente de poder facturar/cobrar.')

    # Mapa código de permiso -> (campo, etiqueta, descripción)
    PERMISOS = {
        'facturar': ('perm_facturar', 'Facturar y cobrar',
                     'Abrir pedidos, agregar productos y cobrar ventas.'),
        'cambiar_precio': ('perm_cambiar_precio', 'Cambiar precios',
                           'Modificar el precio de los productos al vender.'),
        'cortesia': ('perm_cortesia', 'Dar cortesías',
                     'Marcar productos o ventas completas como cortesía (gratis).'),
        'descuento': ('perm_descuento', 'Aplicar descuentos',
                      'Aplicar descuentos manuales al pedido.'),
        'trasladar_mesas': ('perm_trasladar_mesas', 'Trasladar mesas',
                            'Mover pedidos de una mesa a otra.'),
        'cancelar_pedido': ('perm_cancelar_pedido', 'Cancelar pedidos',
                            'Cancelar pedidos abiertos.'),
        'productos': ('perm_productos', 'Gestionar productos',
                      'Crear, editar y eliminar productos, categorías y unidades.'),
        'inventario': ('perm_inventario', 'Gestionar inventario',
                       'Registrar movimientos y consumo interno.'),
        'reportes': ('perm_reportes', 'Ver reportes',
                     'Acceder a reportes y exportaciones.'),
        'caja': ('perm_caja', 'Caja',
                 'Apertura, cierre y egresos de caja.'),
        'configuracion': ('perm_configuracion', 'Configuración',
                          'Editar la configuración del sistema.'),
        'modificar_otros_pedidos': ('perm_modificar_otros_pedidos',
                                    'Modificar mesas de otros',
                                    'Operar mesas/pedidos de otros vendedores.'),
        'ver_totales_caja': ('perm_ver_totales_caja', 'Ver totales de caja',
                            'Ver el dinero esperado y los totales al cerrar la caja.'),
        'ver_facturas': ('perm_ver_facturas', 'Ver facturas',
                         'Consultar y ver el detalle de las facturas emitidas.'),
    }

    @classmethod
    def permisos_para_form(cls):
        """Devuelve lista de (campo, etiqueta, descripción) para el formulario."""
        return [(datos[0], datos[1], datos[2])
                for codigo, datos in cls.PERMISOS.items()]

    def puede(self, codigo):
        """Indica si el vendedor tiene el permiso dado.

        Los administradores (is_staff o is_superuser) siempre tienen
        todos los permisos.
        """
        usuario = self.usuario
        if usuario and (usuario.is_staff or usuario.is_superuser):
            return True
        campo = self.PERMISOS.get(codigo)
        if not campo:
            return False
        return bool(getattr(self, campo[0], False))

    class Meta:
        verbose_name = 'Vendedor'
        verbose_name_plural = 'Vendedores'
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['cedula']),
            models.Index(fields=['activo']),
        ]

    def __str__(self):
        return f'{self.nombre} {self.apellidos}'

    def save(self, *args, **kwargs):
        """Sincroniza el usuario Django al guardar."""
        if not self.usuario_id:
            user = User.objects.create_user(
                username=self.cedula,
                first_name=self.nombre,
                last_name=self.apellidos,
            )
            self.usuario = user
        else:
            self.usuario.username = self.cedula
            self.usuario.first_name = self.nombre
            self.usuario.last_name = self.apellidos
            self.usuario.is_active = self.activo
            self.usuario.save()
        super().save(*args, **kwargs)
