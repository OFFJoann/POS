"""
URLs de la aplicación caja.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.estado_caja, name='estado_caja'),
    path('abrir/', views.abrir_caja, name='abrir_caja'),
    path('cerrar/', views.cerrar_caja, name='cerrar_caja'),
    path('egresos/', views.lista_egresos, name='lista_egresos'),
    path('egresos/registrar/', views.registrar_egreso, name='registrar_egreso'),
    path('egresos/<int:pk>/editar/', views.editar_egreso, name='editar_egreso'),
    path('egresos/<int:pk>/eliminar/', views.eliminar_egreso, name='eliminar_egreso'),
    path('egresos/categorias/', views.gestionar_categorias_egreso, name='gestionar_categorias_egreso'),
    path('egresos/categorias/eliminar/<int:pk>/', views.eliminar_categoria_egreso, name='eliminar_categoria_egreso'),
]
