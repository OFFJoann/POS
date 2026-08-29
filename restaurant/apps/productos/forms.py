from django import forms
from django.forms import inlineformset_factory
from .models import Producto, Categoria, UnidadMedida, ComboComponente


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'codigo', 'nombre', 'categoria', 'unidad', 'es_combo',
            'precio_venta', 'costo', 'comision', 'stock_actual',
            'stock_minimo', 'imagen', 'estado'
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'unidad': forms.Select(attrs={'class': 'form-select'}),
            'precio_venta': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '1'
            }),
            'costo': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '1'
            }),
            'comision': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '1'
            }),
            'stock_actual': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '1'
            }),
            'stock_minimo': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '1'
            }),
            'imagen': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }


class ComboComponenteForm(forms.ModelForm):
    class Meta:
        model = ComboComponente
        fields = ['producto', 'cantidad']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 1, 'step': 1
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['producto'].queryset = Producto.objects.exclude(
            es_combo=True
        ).order_by('nombre')


ComboComponenteFormSet = inlineformset_factory(
    Producto, ComboComponente, fk_name='combo', form=ComboComponenteForm,
    fields=['producto', 'cantidad'], extra=1, can_delete=True
)


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3
            }),
        }


class UnidadMedidaForm(forms.ModelForm):
    class Meta:
        model = UnidadMedida
        fields = ['nombre', 'abreviatura']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'abreviatura': forms.TextInput(attrs={'class': 'form-control'}),
        }
