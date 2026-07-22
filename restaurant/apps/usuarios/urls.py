"""
URLs de la aplicación usuarios.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('acceder/', views.AccederView.as_view(), name='acceder'),
    path('salir/', views.salir, name='salir'),
    path('', views.dashboard, name='dashboard'),
    path('usuarios/', views.lista_vendedores, name='lista_vendedores'),
    path('usuarios/crear/', views.crear_vendedor, name='crear_vendedor'),
    path('usuarios/<int:pk>/editar/', views.editar_vendedor, name='editar_vendedor'),
    path('usuarios/<int:pk>/eliminar/', views.eliminar_vendedor, name='eliminar_vendedor'),
]
