from django.urls import path

from . import views

urlpatterns = [
    path('', views.lista_creditos, name='lista_creditos'),
    path('<int:credito_id>/', views.detalle_credito, name='detalle_credito'),
    path('<int:credito_id>/abonar/', views.vista_registrar_abono,
         name='registrar_abono'),
    path('<int:credito_id>/recordatorio/', views.vista_enviar_recordatorio,
         name='enviar_recordatorio'),
]
