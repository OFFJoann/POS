from django import forms
from .models import Producto, Categoria, UnidadMedida


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'codigo', 'nombre', 'categoria', 'unidad',
            'precio_venta', 'costo', 'stock_actual',
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
