# Generated for email + 2FA login

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0008_vendedor_perm_eliminar_productos'),
    ]

    operations = [
        migrations.AddField(
            model_name='vendedor',
            name='email',
            field=models.EmailField(blank=True, help_text='Correo con el que inicia sesión el vendedor', max_length=254, null=True, verbose_name='Correo'),
        ),
        migrations.AddField(
            model_name='vendedor',
            name='totp_secret',
            field=models.CharField(blank=True, default='', help_text='Secreto TOTP para autenticación de dos factores (vacío = 2FA desactivado)', max_length=64, verbose_name='Secreto 2FA'),
        ),
    ]