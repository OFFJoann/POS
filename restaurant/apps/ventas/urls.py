"""
URLs de la aplicación ventas.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('facturas/', views.lista_facturas, name='lista_facturas'),
    path('factura/<int:factura_id>/', views.ver_factura, name='ver_factura'),
    path('factura/<int:factura_id>/pdf/', views.factura_pdf, name='factura_pdf'),
    path('buscar/', views.buscar_facturas, name='buscar_facturas'),
]
