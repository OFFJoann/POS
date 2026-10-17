"""URLs del servidor central de licencias."""
from django.urls import path

from . import api, views

urlpatterns = [
    # API pública que consultan los POS (sin autenticación)
    path('api/licencia/', views.api_licencia, name='api_licencia'),

    # API del dashboard React (requiere sesión de superusuario)
    path('api/panel/login/', api.panel_login, name='panel_login'),
    path('api/panel/logout/', api.panel_logout, name='panel_logout'),
    path('api/panel/sesion/', api.panel_sesion, name='panel_sesion'),
    path('api/panel/configuracion/', api.panel_configuracion,
         name='panel_configuracion'),
    path('api/panel/dashboard/', api.panel_dashboard, name='panel_dashboard'),
    path('api/panel/licencias/', api.panel_licencias, name='panel_licencias'),
    path('api/panel/licencias/acciones/', api.panel_licencias_acciones,
         name='panel_licencias_acciones'),
    path('api/panel/licencias/<int:pk>/', api.panel_licencia_detalle,
         name='panel_licencia_detalle'),
]