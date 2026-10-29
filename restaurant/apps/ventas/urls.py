"""
URLs de la aplicación ventas.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('facturas/', views.lista_facturas, name='lista_facturas'),
    path('factura/<int:factura_id>/', views.ver_factura, name='ver_factura'),
    path('factura/<int:factura_id>/anular/', views.anular_factura_view, name='anular_factura'),
    path('factura/<int:factura_id>/cambiar-fecha/', views.cambiar_fecha_factura_view, name='cambiar_fecha_factura'),
    path('factura/<int:factura_id>/pdf/', views.factura_pdf, name='factura_pdf'),
    path('factura/<int:factura_id>/enviar/', views.enviar_factura_correo, name='enviar_factura_correo'),
    path('buscar/', views.buscar_facturas, name='buscar_facturas'),
    path('mis-comisiones/', views.mis_comisiones, name='mis_comisiones'),
]
