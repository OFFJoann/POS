"""Formularios del módulo de créditos."""
from django import forms


class CreditoPreexistenteForm(forms.Form):
    """Alta de un crédito ya existente (venta antigua no registrada).

    No lleva cuotas ni frecuencia: solo el saldo que el cliente debe. Sus
    abonos sí cuentan como ventas del día.
    """
    nombre = forms.CharField(
        label='Nombre del cliente', max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    monto = forms.DecimalField(
        label='Monto del crédito', max_digits=12, decimal_places=2, min_value=0.01,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'inputmode': 'decimal',
            'step': '0.01', 'min': '0.01',
        }),
    )
    correo = forms.EmailField(
        label='Correo', required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
    )
    observaciones = forms.CharField(
        label='Observaciones', required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )
