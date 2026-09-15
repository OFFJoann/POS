# Auto-solicitud en caja: campos mensaje, version y updated_at

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mesas', '0005_pedido_sesion_inicio'),
    ]

    operations = [
        migrations.AddField(
            model_name='solicitudpedido',
            name='mensaje',
            field=models.CharField(blank=True, default='', help_text='Mensaje descriptivo para la notificación en caja', max_length=255, verbose_name='Mensaje'),
        ),
        migrations.AddField(
            model_name='solicitudpedido',
            name='version',
            field=models.PositiveIntegerField(default=0, help_text='Se incrementa cada vez que se agregan productos. Usado para re-notificar al receptor.', verbose_name='Versión'),
        ),
        migrations.AddField(
            model_name='solicitudpedido',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Actualizado'),
        ),
    ]