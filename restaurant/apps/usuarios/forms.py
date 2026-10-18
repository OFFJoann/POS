"""
Formularios de la aplicación usuarios.
"""
from django import forms
from .models import Vendedor

CAMPOS_BASICOS = ['nombre', 'apellidos', 'cedula', 'email', 'telefono', 'activo']


class AccesoForm(forms.Form):
    """Formulario para iniciar sesión con correo y contraseña."""
    email = forms.EmailField(
        label='Correo',
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'tucorreo@empresa.com',
            'autofocus': True,
            'autocomplete': 'email',
        })
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': '••••••••',
            'autocomplete': 'current-password',
        })
    )


class VendedorForm(forms.ModelForm):
    """Formulario para crear y editar vendedores."""

    CAMPOS_BASICOS = CAMPOS_BASICOS

    password = forms.CharField(
        label='Contraseña',
        required=False,
        help_text='Déjala vacía para no cambiar la contraseña. '
                  'Al crear un vendedor es obligatoria.',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 'autocomplete': 'new-password'
        }),
    )

    class Meta:
        model = Vendedor
        fields = CAMPOS_BASICOS + [
            'es_receptor_pedidos',
            'perm_facturar', 'perm_cambiar_precio', 'perm_cortesia',
            'perm_descuento', 'perm_trasladar_mesas', 'perm_cancelar_pedido',
            'perm_productos', 'perm_inventario', 'perm_reportes',
            'perm_caja', 'perm_configuracion', 'perm_ver_totales_caja',
            'perm_modificar_otros_pedidos', 'perm_ver_facturas',
            'perm_eliminar_productos', 'perm_credito',
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
            'email': forms.EmailInput(attrs={
                'class': 'form-control', 'placeholder': 'tucorreo@empresa.com'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Teléfono'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['email'].initial = self.instance.email
        self.fields['cedula'].required = True
        self.fields['email'].required = True

    def clean_cedula(self):
        """Valida que la cédula sea única."""
        cedula = self.cleaned_data['cedula']
        instance = getattr(self, 'instance', None)
        qs = Vendedor.objects.filter(cedula=cedula)
        if instance and instance.pk:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise forms.ValidationError('Ya existe un vendedor con esta cédula.')
        return cedula

    def clean_email(self):
        """Valida que el correo sea único."""
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if not email:
            raise forms.ValidationError('El correo es obligatorio.')
        instance = getattr(self, 'instance', None)
        qs = Vendedor.objects.filter(email__iexact=email)
        if instance and instance.pk:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise forms.ValidationError('Ya existe un vendedor con este correo.')
        return email

    def clean_password(self):
        """Valida que al crear el vendedor se especifique una contraseña."""
        password = self.cleaned_data['password']
        if not self.instance.pk and not password:
            raise forms.ValidationError('La contraseña es obligatoria al crear un vendedor.')
        if password and len(password) < 6:
            raise forms.ValidationError('La contraseña debe tener al menos 6 caracteres.')
        return password

    def save(self, commit=True):
        """Guarda el vendedor y sincroniza email y contraseña en el User."""
        vendedor = super().save(commit=False)
        vendedor.email = (self.cleaned_data['email'] or '').strip().lower()
        password = self.cleaned_data.get('password')
        if commit:
            vendedor.save()
            user = vendedor.usuario
            user.email = vendedor.email
            if password:
                user.set_password(password)
            user.save()
        else:
            # Se guarda de inmediato para poder asociar el User correctamente.
            vendedor.save()
        return vendedor