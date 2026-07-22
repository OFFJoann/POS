"""
Formularios de la aplicación inventario.
"""
from django import forms
from .models import MovimientoInventario, ConsumoInterno
from apps.productos.models import Producto
from apps.usuarios.models import Vendedor


class MovimientoInventarioForm(forms.ModelForm):
    """Formulario para registrar movimientos de inventario."""
    class Meta:
        model = MovimientoInventario
        fields = ['producto', 'tipo', 'cantidad', 'motivo', 'descripcion']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-select'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0.01'
            }),
            'motivo': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3
            }),
        }

    def clean_cantidad(self):
        """Valida que la cantidad sea positiva."""
        cantidad = self.cleaned_data['cantidad']
        if cantidad <= 0:
            raise forms.ValidationError('La cantidad debe ser mayor a cero.')
        return cantidad

    def clean(self):
        """Valida que haya stock suficiente para salidas."""
        cleaned = super().clean()
        tipo = cleaned.get('tipo')
        producto = cleaned.get('producto')
        cantidad = cleaned.get('cantidad')

        if tipo == 'salida' and producto and cantidad:
            if producto.stock_actual < cantidad:
                raise forms.ValidationError(
                    f'Stock insuficiente. Stock actual: {producto.stock_actual}'
                )
        return cleaned


class ConsumoInternoForm(forms.ModelForm):
    """Formulario para registrar consumo interno (hidratación)."""
    class Meta:
        model = ConsumoInterno
        fields = ['producto', 'cantidad', 'empleado']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '1', 'min': '1'
            }),
            'empleado': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['empleado'].queryset = Vendedor.objects.filter(activo=True)
        self.fields['empleado'].required = True
        self.fields['empleado'].empty_label = 'Seleccionar empleado'

    def clean_cantidad(self):
        cantidad = self.cleaned_data['cantidad']
        if cantidad <= 0:
            raise forms.ValidationError('La cantidad debe ser mayor a cero.')
        return cantidad

    def clean(self):
        cleaned = super().clean()
        producto = cleaned.get('producto')
        cantidad = cleaned.get('cantidad')
        if producto and cantidad and producto.stock_actual < cantidad:
            raise forms.ValidationError(
                f'Stock insuficiente. Stock actual: {producto.stock_actual}'
            )
        return cleaned
