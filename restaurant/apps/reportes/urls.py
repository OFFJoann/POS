"""
URLs de la aplicación reportes.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_reportes, name='dashboard_reportes'),
    path('ventas/', views.reporte_ventas, name='reporte_ventas'),
    path('ventas/exportar/excel/', views.exportar_ventas_excel, name='exportar_ventas_excel'),
    path('ventas/exportar/pdf/', views.exportar_ventas_pdf, name='exportar_ventas_pdf'),
    path('productos/', views.reporte_productos, name='reporte_productos'),
    path('productos/exportar/excel/', views.exportar_productos_excel, name='exportar_productos_excel'),
    path('mesero/<int:vendedor_id>/', views.reporte_por_mesero, name='reporte_por_mesero'),
    path('api/datos/', views.datos_dashboard_api, name='datos_dashboard_api'),
]
