"""
URLs de la aplicación mesas.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.vista_mesas, name='vista_mesas'),
    path('gestionar/', views.gestion_mesas, name='gestion_mesas'),
    path('gestionar/<int:mesa_id>/eliminar/', views.eliminar_mesa, name='eliminar_mesa'),
    path('estado/', views.estado_mesas_api, name='estado_mesas_api'),
    path('<int:mesa_id>/pedido/', views.abrir_pedido, name='abrir_pedido'),
    path('<int:mesa_id>/liberar/', views.liberar_mesa, name='liberar_mesa'),
    path('pedido/<int:pedido_id>/', views.detalle_pedido, name='detalle_pedido'),
    path('pedido/<int:pedido_id>/agregar/', views.agregar_producto, name='agregar_producto'),
    path('pedido/<int:pedido_id>/quitar/<int:detalle_id>/', views.quitar_producto, name='quitar_producto'),
    path('pedido/<int:pedido_id>/descuento/', views.aplicar_descuento, name='aplicar_descuento'),
    path('pedido/<int:pedido_id>/observaciones/', views.guardar_observaciones, name='guardar_observaciones'),
    path('pedido/<int:pedido_id>/cancelar/', views.cancelar_pedido, name='cancelar_pedido'),
    path('pedido/<int:pedido_id>/cobrar/', views.cobrar_pedido, name='cobrar_pedido'),
    path('pedido/<int:pedido_id>/pago-parcial/', views.pago_parcial, name='pago_parcial'),
    path('pedido/<int:pedido_id>/cambiar-mesero/', views.cambiar_mesero, name='cambiar_mesero'),
]
