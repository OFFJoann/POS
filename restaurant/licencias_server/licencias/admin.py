"""Panel de administración: gestión rápida de licencias."""
from datetime import timedelta

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, UserChangeForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.urls import path
from django.utils import timezone

from .api import DIAS_MENSUALIDAD
from .models import Licencia, UsuarioPanel
from .views import config_servidor


@admin.register(Licencia)
class LicenciaAdmin(admin.ModelAdmin):
    list_display = (
        'codigo', 'cliente', 'fecha_inicio', 'fecha_vencimiento',
        'dias_restantes', 'limite_vendedores', 'mensualidad', 'activa',
    )
    list_filter = ('activa',)
    search_fields = ('codigo', 'cliente')
    date_hierarchy = 'fecha_vencimiento'
    ordering = ('fecha_vencimiento',)
    change_list_template = 'licencias/change_list.html'
    fieldsets = (
        (None, {'fields': ('codigo', 'cliente', 'activa')}),
        ('Vigencia', {'fields': ('fecha_inicio', 'fecha_vencimiento', 'limite_vendedores')}),
        ('Facturación', {'fields': ('mensualidad',)}),
        ('Otros', {'fields': ('features',)}),
    )
    actions = [
        'actualizar_mensualidad', 'extender_30_dias', 'extender_60_dias',
        'extender_90_dias', 'pausar', 'reactivar',
    ]

    def get_urls(self):
        return [
            path(
                'servidor/',
                self.admin_site.admin_view(config_servidor),
                name='licencias_config_servidor',
            ),
        ] + super().get_urls()

    @admin.display(description='Días restantes')
    def dias_restantes(self, obj):
        if obj.dias_restantes is None:
            return '—'
        if obj.dias_restantes < 0:
            return f'{abs(obj.dias_restantes)}d vencida'
        return f'{obj.dias_restantes}d'

    def _extender(self, request, queryset, dias):
        hoy = timezone.localdate()
        renovadas = 0
        for lic in queryset:
            base = lic.fecha_vencimiento or hoy
            if base < hoy:
                base = hoy  # si está vencida, se renueva desde hoy
            lic.fecha_vencimiento = base + timedelta(days=dias)
            lic.activa = True
            lic.save(update_fields=['fecha_vencimiento', 'activa'])
            renovadas += 1
        self.message_user(
            request, f'{renovadas} licencia(s) extendidas {dias} días.')

    @admin.action(description=f'Actualizar mensualidad (+{DIAS_MENSUALIDAD} días)')
    def actualizar_mensualidad(self, request, queryset):
        """Un mes pagado: extiende y reactiva, igual que el botón del panel."""
        self._extender(request, queryset, DIAS_MENSUALIDAD)

    @admin.action(description='Extender 30 días')
    def extender_30_dias(self, request, queryset):
        self._extender(request, queryset, 30)

    @admin.action(description='Extender 60 días')
    def extender_60_dias(self, request, queryset):
        self._extender(request, queryset, 60)

    @admin.action(description='Extender 90 días')
    def extender_90_dias(self, request, queryset):
        self._extender(request, queryset, 90)

    @admin.action(description='Pausar / bloquear')
    def pausar(self, request, queryset):
        n = queryset.update(activa=False)
        self.message_user(request, f'{n} licencia(s) pausadas.')

    @admin.action(description='Reactivar')
    def reactivar(self, request, queryset):
        n = queryset.update(activa=True)
        self.message_user(request, f'{n} licencia(s) reactivadas.')


@admin.register(UsuarioPanel)
class UsuarioPanelAdmin(admin.ModelAdmin):
    """Listado de quién entra al panel y con qué permisos.

    El alta y el cambio de rol se hacen en la propia ficha del usuario
    (`/admin/auth/user/`), donde el rol es un campo más. Esta vista sirve para
    ver el reparto de un vistazo.
    """
    list_display = ('usuario', 'rol', 'activo', 'acceso_admin')
    list_filter = ('rol',)
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name')
    ordering = ('usuario__username',)
    list_select_related = ('usuario',)

    def has_add_permission(self, request):
        # El perfil se crea desde la ficha del usuario, no aquí.
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description='Activo', boolean=True)
    def activo(self, obj):
        return obj.usuario.is_active

    @admin.display(description='Entra a /admin/', boolean=True)
    def acceso_admin(self, obj):
        return obj.usuario.is_staff


class _RolEnFormulario(forms.Form):
    """Rol del panel, mezclado en los formularios de usuario de Django."""
    rol = forms.ChoiceField(
        choices=UsuarioPanel.ROLES,
        label='Rol en el panel',
        help_text='Visualizador solo lee. Administrador puede emitir, editar y '
                  'cobrar licencias. Lo de menos permisos es el valor por defecto.',
    )

    def __init__(self, *args, **kwargs):
        inicial = kwargs.pop('rol_inicial', UsuarioPanel.VISUALIZADOR)
        super().__init__(*args, **kwargs)
        self.fields['rol'].initial = inicial


class _FormAltaConRol(_RolEnFormulario, UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username',)


class _FormEdicionConRol(_RolEnFormulario, UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'


admin.site.unregister(User)


@admin.register(User)
class UsuarioAdmin(UserAdmin):
    """Usuarios del panel con su rol, todo en un solo formulario.

    Se mezcla el rol en el formulario de alta y de edición de Django para no
    obligar a crear la cuenta y luego ir a otra pantalla a asignarle permisos.
    Lo de menos permisos es el valor por defecto: una cuenta recién creada no
    escribe nada hasta que alguien la promociona a administrador.
    """
    form = _FormEdicionConRol
    add_form = _FormAltaConRol
    list_display = ('username', 'nombre', 'email', 'rol', 'is_active', 'is_staff')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'panel__rol')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'rol', 'password1', 'password2'),
        }),
        ('Nombre', {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name', 'email'),
        }),
        ('Permisos', {
            'classes': ('wide',),
            # El superusuario se apaga a propósito: al panel se entra por el
            # rol, no saltándose los permisos.
            'fields': ('is_active',),
        }),
    )
    fieldsets = UserAdmin.fieldsets + (
        ('Panel de licencias', {'fields': ('rol',)}),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'rol' in form.base_fields:
            # Al editar, mostrar el rol que ya tiene y no un valor en blanco.
            perfil = getattr(obj, 'panel', None)
            if perfil is not None:
                form.base_fields['rol'].initial = perfil.rol
        return form

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if 'rol' in form.cleaned_data:
            UsuarioPanel.objects.update_or_create(
                usuario=obj, defaults={'rol': form.cleaned_data['rol']})

    @admin.display(description='Nombre', ordering='first_name')
    def nombre(self, obj):
        return (obj.get_full_name() or '').strip() or '—'

    @admin.display(description='Rol', ordering='panel__rol')
    def rol(self, obj):
        if obj.pk is None:
            return UsuarioPanel.VISUALIZADOR
        perfil = getattr(obj, 'panel', None)
        if perfil is not None:
            return perfil.get_rol_display()
        # Sin ficha solo entra un superusuario anterior a los roles.
        return 'Administrador' if obj.is_superuser else 'Sin acceso'

