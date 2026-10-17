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
    """Formulario para crear/editar mesa o caja."""
    class Meta:
        model = Mesa
        fields = ['numero', 'tipo']
        widgets = {
            'numero': forms.NumberInput(attrs={
                'class': 'form-control', 'placeholder': 'Número',
                'min': '1', 'step': '1'
            }),
            'tipo': forms.Select(attrs={
                'class': 'form-select',
            }),
        }

    def clean(self):
        cleaned = super().clean()
        numero = cleaned.get('numero')
        tipo = cleaned.get('tipo') or 'mesa'
        if numero is not None and Mesa.objects.filter(
            numero=numero, tipo=tipo
        ).exclude(pk=self.instance.pk).exists():
            etiqueta = 'caja' if tipo == 'caja' else 'mesa'
            self.add_error(
                'numero',
                f'Ya existe una {etiqueta} con el número {numero}.')
        return cleaned
