"""
Management command para limpiar datos de prueba y dejar el sistema listo
para empezar con datos reales.

Conserva:
  - El usuario admin (Vendedor con cédula '1234567890')
  - Todas las mesas

Elimina todo lo demás: productos, categorías, facturas, pedidos, etc.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = 'Elimina datos de prueba conservando admin y mesas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true',
            help='Ejecuta sin pedir confirmación',
        )

    def handle(self, *args, **options):
        from django.contrib.auth.models import User
        from apps.usuarios.models import Vendedor
        from apps.mesas.models import DetallePedido, Pedido, Mesa
        from apps.ventas.models import Factura, Pago
        from apps.inventario.models import MovimientoInventario, ConsumoInterno
        from apps.caja.models import Egreso, AperturaCaja, CategoriaEgreso
        from apps.productos.models import Producto, Categoria, UnidadMedida

        admin_vendedor = Vendedor.objects.filter(cedula='1234567890').first()
        if not admin_vendedor:
            raise CommandError('No se encontró el usuario admin (cédula 1234567890).')

        admin_user = admin_vendedor.usuario

        if not options['force']:
            confirm = input(
                f'\n⚠️  Esto ELIMINARÁ todos los datos del sistema excepto:\n'
                f'   - Usuario admin: {admin_vendedor.nombre} (cédula {admin_vendedor.cedula})\n'
                f'   - {Mesa.objects.count()} mesas\n\n'
                f'   ¿Estás seguro? (escribe "si" para continuar): '
            )
            if confirm.lower() != 'si':
                self.stdout.write(self.style.WARNING('Operación cancelada.'))
                return

        with transaction.atomic():
            # Orden de eliminación respetando FK
            eliminados = {}

            eliminados['detalles_pedido'] = DetallePedido.objects.all().delete()[0]
            eliminados['pagos'] = Pago.objects.all().delete()[0]
            eliminados['facturas'] = Factura.objects.all().delete()[0]
            eliminados['pedidos'] = Pedido.objects.all().delete()[0]
            eliminados['movimientos_inventario'] = MovimientoInventario.objects.all().delete()[0]
            eliminados['consumos_internos'] = ConsumoInterno.objects.all().delete()[0]
            eliminados['egresos'] = Egreso.objects.all().delete()[0]
            eliminados['aperturas_caja'] = AperturaCaja.objects.all().delete()[0]
            eliminados['productos'] = Producto.objects.all().delete()[0]
            eliminados['categorias'] = Categoria.objects.all().delete()[0]
            eliminados['unidades_medida'] = UnidadMedida.objects.all().delete()[0]
            eliminados['categorias_egreso'] = CategoriaEgreso.objects.all().delete()[0]

            # Eliminar vendedores excepto el admin
            otros = Vendedor.objects.exclude(pk=admin_vendedor.pk)
            for v in otros:
                v.usuario.delete()  # elimina el User asociado
                v.delete()
            eliminados['vendedores'] = len(otros)

            # Eliminar Users no asociados a ningún Vendedor (excepto admin)
            otros_users = User.objects.exclude(pk=admin_user.pk).filter(vendedor__isnull=True)
            count, _ = otros_users.delete()
            eliminados['usuarios_extra'] = count

        self.stdout.write(self.style.SUCCESS('\n✅ Datos eliminados correctamente.\n'))
        for key, count in eliminados.items():
            if count:
                self.stdout.write(f'   {key}: {count} registro(s) eliminado(s)')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'   Queda: {admin_vendedor.nombre} + {Mesa.objects.count()} mesas listas.'
        ))
