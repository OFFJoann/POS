"""Comando: crear o actualizar una licencia desde la terminal."""
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from licencias.models import Licencia


class Command(BaseCommand):
    help = 'Crea (o actualiza) una licencia para un cliente del POS.'

    def add_arguments(self, parser):
        parser.add_argument('codigo', help='Código de la licencia (LICENCIA_CODIGO del cliente).')
        parser.add_argument('--cliente', default='',
                            help='Nombre visible del negocio.')
        parser.add_argument('--dias', type=int, default=30,
                            help='Días de validez desde hoy (defecto: 30, la venta es mensual).')
        parser.add_argument('--vendedores', type=int, default=5,
                            help='Límite de vendedores (defecto: 5).')
        parser.add_argument('--mensualidad', default='0',
                            help='Precio mensual que paga el cliente (defecto: 0).')

    def handle(self, *args, **opts):
        try:
            mensualidad = Decimal(str(opts['mensualidad']).replace(',', '.'))
        except (InvalidOperation, ValueError):
            raise CommandError(
                f'--mensualidad inválido: {opts["mensualidad"]!r}')
        if mensualidad < 0:
            raise CommandError('--mensualidad no puede ser negativo.')

        hoy = timezone.localdate()
        lic, creada = Licencia.objects.update_or_create(
            codigo=opts['codigo'].strip(),
            defaults={
                'cliente': opts['cliente'].strip() or opts['codigo'].strip(),
                'fecha_inicio': hoy,
                'fecha_vencimiento': hoy + timedelta(days=opts['dias']),
                'limite_vendedores': opts['vendedores'],
                'mensualidad': mensualidad,
                'activa': True,
            },
        )
        estado = 'Creada' if creada else 'Actualizada'
        self.stdout.write(self.style.SUCCESS(
            f'{estado} licencia {lic.codigo} - vence '
            f'{lic.fecha_vencimiento} - {lic.limite_vendedores} vendedores - '
            f'{lic.mensualidad} al mes.'))