from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import CadastroForm


def cadastrar(request):
    if request.user.is_authenticated:
        return redirect('aprendizagem:painel')
    form = CadastroForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        usuario = form.save()
        login(request, usuario)
        messages.success(request, 'Conta criada. Bem-vindo à Aprenda+!')
        return redirect('cursos:catalogo')
    return render(request, 'contas/cadastro.html', {'form': form})
