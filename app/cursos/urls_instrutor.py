from django.urls import path

from . import views

app_name = 'instrutor'
urlpatterns = [
    path('', views.painel_instrutor, name='painel_instrutor'),
    path('novo/', views.editar_curso, name='criar'),
    path('curso/<int:curso_id>/', views.gerenciar, name='gerenciar'),
    path('curso/<int:curso_id>/editar/', views.editar_curso, name='editar'),
    path('curso/<int:curso_id>/publicar/', views.publicar, name='publicar'),
    path('curso/<int:curso_id>/excluir/', views.excluir, name='excluir'),
    path('curso/<int:curso_id>/modulo/novo/', views.editar_modulo, name='modulo_criar'),
    path('curso/<int:curso_id>/modulo/<int:modulo_id>/editar/', views.editar_modulo, name='modulo_editar'),
    path('curso/<int:curso_id>/modulo/<int:modulo_id>/excluir/', views.excluir, name='modulo_excluir'),
    path('modulo/<int:modulo_id>/aula/<str:tipo>/nova/', views.editar_aula, name='aula_criar'),
    path('modulo/<int:modulo_id>/aula/<int:aula_id>/editar/', views.editar_aula, name='aula_editar'),
    path('curso/<int:curso_id>/aula/<int:aula_id>/excluir/', views.excluir, name='aula_excluir'),
    path('aviso/<int:aviso_id>/ler/', views.ler_aviso, name='ler_aviso'),
]
