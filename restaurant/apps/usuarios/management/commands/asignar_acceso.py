"""
Comando para asignar (o cambiar) el correo y la contraseña
de un vendedor por su cédula.

Útil para configurar el acceso del administrador desde el shell
cuando aún no existe conexión web con el nuevo login.

Uso:
  python manage.py asignar_acceso --cedula 1234567890 \
      --email admin@empresa.com --password Segura123
"""
from django.core.management.base import BaseCommand, CommandError
from apps.usuarios.models import Vendedor


class Command(BaseCommand):
    help = 'Asigna correo y contraseña de acceso a un vendedor (por cédula).'

    def add_arguments(self, parser):
        parser.add_argument('--cedula', required=True, help='Cédula del vendedor')
        parser.add_argument('--email', required=True, help='Correo de acceso')
        parser.add_argument('--password', required=True, help='Nueva contraseña')

    def handle(self, *args, **options):
        cedula = options['cedula']
        email = options['email'].strip().lower()
        password = options['password']

        vendedor = Vendedor.objects.filter(cedula=cedula).first()
        if not vendedor:
            raise CommandError(f'No existe un vendedor con cédula {cedula}.')

        vendedor.email = email
        vendedor.save()
        user = vendedor.usuario
        user.email = email
        user.set_password(password)
        user.save()

        self.stdout.write(self.style.SUCCESS(
            f'✅ Acceso actualizado para {vendedor.nombre} {vendedor.apellidos} '
            f'({email}) — la contraseña fue cambiada.'
        ))
        if vendedor.totp_secret:
            self.stdout.write(self.style.WARNING(
                '⚠️  El vendedor tiene 2FA activado: además necesitará el código '
                'de la aplicación de autenticación al iniciar sesión.'
            ))