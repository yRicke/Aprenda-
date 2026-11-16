from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from . import views

app_name = 'contas'
urlpatterns = [
    path('entrar/', LoginView.as_view(template_name='contas/login.html'), name='login'),
    path('sair/', LogoutView.as_view(), name='logout'),
    path('cadastro/', views.cadastrar, name='cadastro'),
]
