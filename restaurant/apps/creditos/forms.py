"""Formularios del módulo de créditos.

El cliente de un crédito no va en estos formularios: se elige con el selector
compartido `creditos/_selector_cliente.html` (campos `cliente_id`,
`cliente_nombre` y `cliente_correo`) y se resuelve con
`services.resolver_cliente`.
"""
import re

from django import forms


def normalizar_monto(valor):
    """Convierte un monto escrito con puntos de miles a formato decimal.

    "1.250.000" -> "1250000", "3.333,34" -> "3333.34", "15000.50" se deja
    igual (un solo punto seguido de 1-2 dígitos se toma como decimal).
    """
    valor = str(valor or '').strip().replace(' ', '').replace('$', '')
    if ',' in valor:
        return valor.replace('.', '').replace(',', '.')
    if re.fullmatch(r'\d{1,3}(\.\d{3})+', valor):
        return valor.replace('.', '')
    return valor


class MontoField(forms.DecimalField):
    """DecimalField que acepta montos con puntos de miles (1.250.000)."""

    def to_python(self, value):
        if isinstance(value, str):
            value = normalizar_monto(value)
        return super().to_python(value)


class ClienteForm(forms.Form):
    """Alta y edición de un cliente de crédito: solo nombre y correo."""
    nombre = forms.CharField(
        label='Nombre', max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    correo = forms.EmailField(
        label='Correo', required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
    )


class CreditoPreexistenteForm(forms.Form):
    """Alta de un crédito ya existente (venta antigua no registrada).

    No lleva cuotas ni frecuencia: solo el saldo que el cliente debe. Sus
    abonos sí cuentan como ventas del día.
    """
    monto = MontoField(
        label='Monto del crédito', max_digits=12, decimal_places=2, min_value=0.01,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'inputmode': 'decimal',
            'data-miles': '', 'autocomplete': 'off',
        }),
    )
    observaciones = forms.CharField(
        label='Observaciones', required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )


class EditarCreditoForm(forms.Form):
    """Edición de un crédito: monto, observaciones y calendario.

    `cuotas_total` y `frecuencia` solo aplican a créditos con calendario; en
    los anotados se quitan del formulario.
    """
    monto = MontoField(
        label='Monto del crédito', max_digits=12, decimal_places=2, min_value=0.01,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'inputmode': 'decimal',
            'data-miles': '', 'autocomplete': 'off',
        }),
    )
    cuotas_total = forms.IntegerField(
        label='Número de cuotas', min_value=1, max_value=120,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
    )
    frecuencia = forms.ChoiceField(
        label='Frecuencia',
        choices=[('mensual', 'Mensual'), ('quincenal', 'Quincenal')],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    observaciones = forms.CharField(
        label='Observaciones', required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )

    def __init__(self, *args, credito=None, **kwargs):
        super().__init__(*args, **kwargs)
        if credito is not None and credito.es_preexistente:
            del self.fields['cuotas_total']
            del self.fields['frecuencia']
