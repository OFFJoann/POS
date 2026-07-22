"""
Formularios de la aplicación usuarios.
"""
from django import forms
from .models import Vendedor


class VendedorForm(forms.ModelForm):
    """Formulario para crear y editar vendedores."""
    class Meta:
        model = Vendedor
        fields = ['nombre', 'apellidos', 'cedula', 'telefono', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Nombre'
            }),
            'apellidos': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Apellidos'
            }),
            'cedula': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Cédula'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Teléfono'
            }),
        }

    def clean_cedula(self):
        """Valida que la cédula sea única."""
        cedula = self.cleaned_data['cedula']
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            if Vendedor.objects.filter(cedula=cedula).exclude(pk=instance.pk).exists():
                raise forms.ValidationError('Ya existe un vendedor con esta cédula.')
        elif Vendedor.objects.filter(cedula=cedula).exists():
            raise forms.ValidationError('Ya existe un vendedor con esta cédula.')
        return cedula
