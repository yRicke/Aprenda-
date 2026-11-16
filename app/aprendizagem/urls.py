from django.urls import path

from . import views

app_name = 'aprendizagem'
urlpatterns = [
    path('', views.painel, name='painel'),
    path('<int:matricula_id>/', views.curso, name='curso'),
    path('<int:matricula_id>/aula/<int:aula_id>/', views.aula, name='aula'),
    path('<int:matricula_id>/concluir/', views.concluir, name='concluir'),
    path('certificado/<uuid:codigo>/', views.certificado, name='certificado'),
]
