"""URLs del servidor central de licencias."""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.generic import RedirectView

from config import panel_urls


def healthz(_request):
    return JsonResponse({'status': 'ok', 'servicio': 'licencias'})


urlpatterns = [
    path('', RedirectView.as_view(url='/panel/', permanent=False)),
    path('healthz/', healthz, name='healthz'),

    # Dashboard React (SPA). Los assets con hash los sirve WhiteNoise.
    re_path(r'^panel/', include(panel_urls.urlpatterns)),

    # Respaldo: Django Admin sigue disponible.
    path('admin/', admin.site.urls),

    path('', include('licencias.urls')),
]