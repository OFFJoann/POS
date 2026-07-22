"""
Modelos de la aplicación usuarios.

Define el perfil de vendedor con autenticación por cédula.
"""
from django.db import models
from django.contrib.auth.models import User


class Vendedor(models.Model):
    """
    Perfil de vendedor del restaurante.

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
