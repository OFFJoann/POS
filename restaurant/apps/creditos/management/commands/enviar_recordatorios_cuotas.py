"""
Comando para enviar los recordatorios de cuotas de crédito.

Avisa un día antes del vencimiento y el día del vencimiento. Cada cuota se
avisa una sola vez por tipo (queda marcada en la base). Pensado para correr
una vez al día con cron.

Uso:
    python manage.py enviar_recordatorios_cuotas
    python manage.py enviar_recordatorios_cuotas --dry-run
"""
from django.core.management.base import BaseCommand

from apps.creditos.services import (
    cuotas_para_recordatorio,
    enviar_recordatorio_cuota,
)


class Command(BaseCommand):
    help = ('Envía los recordatorios de cuotas de crédito: uno un día antes '
            'del vencimiento y otro el día del vencimiento.')

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Muestra lo que se enviaría sin enviar nada.',
        )

    def handle(self, *args, **opts):
        dry = opts['dry_run']
        pendientes = cuotas_para_recordatorio()
        total = 0
        errores = 0

        for tipo, etiqueta in (('antes', 'un día antes'),
                               ('vence', 'el día del vencimiento')):
            for cuota in pendientes[tipo]:
                cliente = cuota.credito.cliente
                correo = cliente.correo
                if dry:
                    self.stdout.write(
                        '[%s] Cuota %s de $%s (%s) -> %s <%s>' % (
                            etiqueta, cuota.numero, cuota.monto_faltante,
                            cliente.nombre, cliente.nombre, correo))
                    total += 1
                    continue
                ok, detalle = enviar_recordatorio_cuota(cuota, tipo)
                if ok:
                    total += 1
                    self.stdout.write(self.style.SUCCESS(
                        'Enviado [%s] a %s (cuota %s)' % (
                            etiqueta, detalle, cuota.numero)))
                else:
                    errores += 1
                    self.stdout.write(self.style.ERROR(
                        'Fallo [%s] para %s: %s' % (etiqueta, correo, detalle)))

        if dry:
            self.stdout.write(self.style.WARNING(
                'Dry run: %d recordatorio(s) por enviar.' % total))
        else:
            self.stdout.write(self.style.SUCCESS(
                'Listo: %d recordatorio(s) enviado(s), %d error(es).' % (
                    total, errores)))
