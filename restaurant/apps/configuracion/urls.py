"""
URLs de la aplicación configuracion.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('configuracion/', views.editar_configuracion, name='editar_configuracion'),
]
