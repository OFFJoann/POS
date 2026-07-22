"""
Formularios de la aplicación mesas.
"""
from django import forms
from .models import Pedido, DetallePedido, Mesa


class AgregarProductoForm(forms.Form):
    """Formulario para agregar productos a un pedido."""
    producto_id = forms.IntegerField(widget=forms.HiddenInput())
    cantidad = forms.DecimalField(
        label='Cantidad',
        max_digits=10, decimal_places=2,
        min_value=0.01,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'step': '1', 'min': '1'
        })
    )


class ObservacionesForm(forms.Form):
    """Formulario para observaciones del pedido."""
    observaciones = forms.CharField(
        label='Observaciones',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'rows': 3,
            'placeholder': 'Observaciones del pedido...'
        })
    )


class DescuentoForm(forms.Form):
    """Formulario para aplicar descuento."""
    descuento = forms.DecimalField(
        label='Descuento',
        max_digits=12, decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'step': '1'
        })
    )


class MesaForm(forms.ModelForm):
    """Formulario para crear/editar mesa."""
    class Meta:
        model = Mesa
        fields = ['numero']
        widgets = {
            'numero': forms.NumberInput(attrs={
                'class': 'form-control', 'placeholder': 'Número de mesa',
                'min': '1', 'step': '1'
            }),
        }

    def clean_numero(self):
        numero = self.cleaned_data['numero']
        if Mesa.objects.filter(numero=numero).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(f'Ya existe una mesa con el número {numero}.')
        return numero
