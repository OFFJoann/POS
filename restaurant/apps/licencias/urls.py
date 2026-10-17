from django.urls import path

from . import views

urlpatterns = [
    path('', views.estado_licencia, name='estado_licencia'),
    path('revalidar/', views.revalidar_licencia, name='revalidar_licencia'),
]