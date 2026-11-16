from django.urls import path

from . import views

app_name = 'cursos'
urlpatterns = [
    path('', views.catalogo, name='catalogo'),
    path('curso/<int:curso_id>/', views.detalhe, name='detalhe'),
]
