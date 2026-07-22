"""
Comando de gestión para inicializar el proyecto.

Crea el superusuario, vendedor admin, carga datos iniciales
y configura todo lo necesario para empezar a usar el sistema.
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth.models import User
from apps.usuarios.models import Vendedor


class Command(BaseCommand):
    help = 'Inicializa el proyecto con datos de ejemplo y configuración básica'

    def add_arguments(self, parser):
        parser.add_argument(
            '--admin-cedula',
            type=str,
            default='1234567890',
            help='Cédula para el administrador'
        )
        parser.add_argument(
            '--admin-nombre',
            type=str,
            default='Admin',
            help='Nombre del administrador'
        )

    def handle(self, *args, **options):
        self.stdout.write('🚀 Inicializando proyecto Restaurant...\n')

        # 1. Migraciones
        self.stdout.write('📦 Ejecutando migraciones...')
        call_command('migrate', verbosity=0)
        self.stdout.write(self.style.SUCCESS('✅ Migraciones ejecutadas'))

        # 2. Cargar fixtures
        self.stdout.write('📥 Cargando datos iniciales...')
        try:
            call_command('loaddata', 'fixtures/datos_iniciales.json', verbosity=0)
            self.stdout.write(self.style.SUCCESS('✅ Datos iniciales cargados'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️  No se pudieron cargar fixtures: {e}'))

        # 3. Crear superusuario y vendedor admin
        cedula = options['admin_cedula']
        nombre = options['admin_nombre']

        if not User.objects.filter(username=cedula).exists():
            self.stdout.write(f'👤 Creando administrador (cédula: {cedula})...')
            user = User.objects.create_superuser(
                username=cedula,
                password='admin123',
                first_name=nombre,
                last_name='Administrador',
            )
            Vendedor.objects.create(
                usuario=user,
                nombre=nombre,
                apellidos='Administrador',
                cedula=cedula,
                telefono='3000000000',
                activo=True,
            )
            self.stdout.write(self.style.SUCCESS(f'✅ Administrador creado: {cedula} / admin123'))
        else:
            self.stdout.write(self.style.WARNING('⚠️  El usuario administrador ya existe'))

        self.stdout.write('\n📋 Resumen:')
        self.stdout.write('   URL: http://localhost:8000/')
        self.stdout.write('   Admin: http://localhost:8000/admin/')
        self.stdout.write(f'   Cédula admin: {cedula}')
        self.stdout.write('   Contraseña admin: admin123')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('🎉 Proyecto listo para usar!'))
