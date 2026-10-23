from django.urls import path

from . import views

urlpatterns = [
    path('', views.lista_creditos, name='lista_creditos'),
    path('nuevo/', views.vista_crear_credito_preexistente,
         name='crear_credito_preexistente'),
    path('clientes/', views.lista_clientes, name='lista_clientes'),
    path('clientes/nuevo/', views.vista_cliente_form, name='crear_cliente'),
    path('clientes/<int:cliente_id>/editar/', views.vista_cliente_form,
         name='editar_cliente'),
    path('<int:credito_id>/', views.detalle_credito, name='detalle_credito'),
    path('<int:credito_id>/editar/', views.vista_editar_credito,
         name='editar_credito'),
    path('<int:credito_id>/eliminar/', views.vista_eliminar_credito,
         name='eliminar_credito'),
    path('<int:credito_id>/abonar/', views.vista_registrar_abono,
         name='registrar_abono'),
    path('<int:credito_id>/abono/<int:abono_id>/editar/',
         views.vista_editar_abono, name='editar_abono'),
    path('<int:credito_id>/recordatorio/', views.vista_enviar_recordatorio,
         name='enviar_recordatorio'),
]
