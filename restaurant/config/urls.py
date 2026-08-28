"""
URLs principales del proyecto El Choli.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.productos.views import carta_digital

urlpatterns = [
    path('admin/', admin.site.urls),
    path('carta/', carta_digital, name='carta_digital'),
    path('configuracion/', include('apps.configuracion.urls')),
    path('', include('apps.usuarios.urls')),
    path('productos/', include('apps.productos.urls')),
    path('inventario/', include('apps.inventario.urls')),
    path('mesas/', include('apps.mesas.urls')),
    path('ventas/', include('apps.ventas.urls')),
    path('caja/', include('apps.caja.urls')),
    path('reportes/', include('apps.reportes.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
