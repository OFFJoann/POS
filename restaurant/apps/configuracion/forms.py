"""
Formularios de la aplicación configuracion.
"""
from django import forms
from .models import Configuracion


class ConfiguracionForm(forms.ModelForm):
    """Formulario para editar la configuración de la empresa."""

    class Meta:
        model = Configuracion
        fields = ['nombre_empresa', 'logo', 'qr_consignacion', 'nit', 'direccion', 'telefono']
        widgets = {
            'nombre_empresa': forms.TextInput(attrs={'class': 'form-control'}),
            'nit': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
        }
