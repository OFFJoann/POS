"""
Formularios de la aplicación usuarios.
"""
from django import forms
from .models import Vendedor

CAMPOS_BASICOS = ['nombre', 'apellidos', 'cedula', 'telefono', 'activo']


class VendedorForm(forms.ModelForm):
    """Formulario para crear y editar vendedores."""

    CAMPOS_BASICOS = CAMPOS_BASICOS

    class Meta:
        model = Vendedor
        fields = CAMPOS_BASICOS + [
            'perm_facturar', 'perm_cambiar_precio', 'perm_cortesia',
            'perm_descuento', 'perm_trasladar_mesas', 'perm_cancelar_pedido',
            'perm_productos', 'perm_inventario', 'perm_reportes',
            'perm_caja', 'perm_configuracion', 'perm_ver_totales_caja',
            'perm_modificar_otros_pedidos', 'perm_ver_facturas',
        ]
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
