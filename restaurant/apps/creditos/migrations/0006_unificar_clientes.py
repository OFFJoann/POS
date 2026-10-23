"""Unifica clientes duplicados para poder elegirlos desde una lista.

Antes el cliente se escribía a mano en cada crédito, así que pueden existir
varios registros de la misma persona. Se consideran el mismo cliente los que
tienen igual nombre (sin distinguir mayúsculas ni espacios extra) e igual
correo. Sus créditos pasan al registro más antiguo y el resto se elimina.
"""
from django.db import migrations


def _clave(cliente):
    nombre = ' '.join((cliente.nombre or '').split()).lower()
    return nombre, (cliente.correo or '').strip().lower()


def unificar_clientes(apps, schema_editor):
    Cliente = apps.get_model('creditos', 'Cliente')
    Credito = apps.get_model('creditos', 'Credito')

    principales = {}
    for cliente in Cliente.objects.order_by('id'):
        clave = _clave(cliente)
        principal = principales.get(clave)
        if principal is None:
            principales[clave] = cliente
            continue
        Credito.objects.filter(cliente=cliente).update(cliente=principal)
        # Conserva datos que solo tenía el duplicado.
        cambios = []
        for campo in ('cedula', 'telefono'):
            if not getattr(principal, campo) and getattr(cliente, campo):
                setattr(principal, campo, getattr(cliente, campo))
                cambios.append(campo)
        if cambios:
            principal.save(update_fields=cambios)
        cliente.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('creditos', '0005_abono_factura'),
    ]

    operations = [
        migrations.RunPython(unificar_clientes, migrations.RunPython.noop),
    ]
