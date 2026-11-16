from django.urls import path

from . import views

app_name = 'compras'
urlpatterns = [
    path('curso/<int:curso_id>/', views.checkout, name='checkout'),
    path('pagamento/<int:solicitacao_id>/consultar/', views.consultar, name='consultar'),
]
