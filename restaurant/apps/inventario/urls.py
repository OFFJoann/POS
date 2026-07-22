"""
URLs de la aplicación inventario.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_inventario, name='lista_inventario'),
    path('movimiento/', views.registrar_movimiento, name='registrar_movimiento'),
    path('historial/', views.historial_inventario, name='historial_inventario'),
    path('buscar/', views.buscar_inventario, name='buscar_inventario'),
    path('consumo-interno/', views.registrar_consumo_interno, name='registrar_consumo_interno'),
]
