"""
URLs de la aplicación productos.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_productos, name='lista_productos'),
    path('crear/', views.crear_producto, name='crear_producto'),
    path('<int:pk>/editar/', views.editar_producto, name='editar_producto'),
    path('<int:pk>/eliminar/', views.eliminar_producto, name='eliminar_producto'),
    path('precios/', views.lista_precios, name='lista_precios'),
    path('buscar/', views.buscar_productos, name='buscar_productos'),
    path('categorias/', views.lista_categorias, name='lista_categorias'),
    path('categorias/crear/', views.crear_categoria, name='crear_categoria'),
    path('unidades/', views.lista_unidades, name='lista_unidades'),
    path('unidades/crear/', views.crear_unidad, name='crear_unidad'),
    path('unidades/<int:pk>/editar/', views.editar_unidad, name='editar_unidad'),
]
