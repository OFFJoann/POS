"""
Formularios de la aplicación caja.
"""
from django import forms
from .models import AperturaCaja, Egreso, CategoriaEgreso


class AperturaCajaForm(forms.ModelForm):
    """Formulario para abrir caja."""
    class Meta:
        model = AperturaCaja
        fields = ['monto_inicial']
        widgets = {
            'monto_inicial': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'step': '1', 'min': '0',
                'placeholder': '0'
            }),
        }

    def clean_monto_inicial(self):
        monto = self.cleaned_data['monto_inicial']
        if monto < 0:
            raise forms.ValidationError('El monto inicial no puede ser negativo.')
        return monto


class EgresoForm(forms.ModelForm):
    """Formulario para registrar egresos."""
    class Meta:
        model = Egreso
        fields = ['categoria', 'metodo_pago', 'valor', 'motivo', 'descripcion', 'soporte']
        widgets = {
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'metodo_pago': forms.Select(attrs={'class': 'form-select'}),
            'valor': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '1', 'min': '1'
            }),
            'motivo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Compra de hielo'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Descripción del egreso...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].required = False
        self.fields['categoria'].empty_label = 'Seleccionar categoría'

    def clean_valor(self):
        valor = self.cleaned_data['valor']
        if valor <= 0:
            raise forms.ValidationError('El valor debe ser mayor a cero.')
        return valor
