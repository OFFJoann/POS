"""
Vistas de la aplicación configuracion.

Permite a los administradores editar la configuración de la empresa
(nombre, logo, etc.) desde una página propia del sistema.
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Configuracion
from .forms import ConfiguracionForm
from apps.usuarios.decorators import admin_required, permiso_required


@login_required
@permiso_required('configuracion')
def editar_configuracion(request):
    """
    Edita la configuración general de la empresa.

    Solo accesible para administradores.
    """
    config = Configuracion.obtener()

    if request.method == 'POST':
        form = ConfiguracionForm(request.POST, request.FILES, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuración actualizada correctamente.')
            return redirect('editar_configuracion')
    else:
        form = ConfiguracionForm(instance=config)

    return render(request, 'configuracion/editar.html', {
        'form': form,
        'config': config,
    })
