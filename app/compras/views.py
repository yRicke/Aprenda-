from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from app.aprendizagem.models import Matricula
from app.cursos.models import Curso

from .forms import CompraForm
from .models import SolicitacaoPagamento
from .services import assinar_oferta, comprar, consultar_pagamento, cotar


@login_required
def checkout(request, curso_id):
    curso = get_object_or_404(Curso, pk=curso_id, publicado=True)
    matricula = Matricula.objects.filter(compra__aluno=request.user, compra__curso=curso).first()
    if matricula:
        return redirect('aprendizagem:curso', matricula.pk)
    cupom, valor = None, curso.preco
    form = CompraForm(request.POST if request.method == 'POST' else None, initial={'token': 'aprovar'})
    if request.method == 'POST' and form.is_valid():
        try:
            if request.POST.get('acao') == 'comprar':
                matricula, aviso = comprar(
                    aluno=request.user, curso_id=curso.pk, oferta=form.cleaned_data['oferta'],
                    token=form.cleaned_data['token'],
                )
                if matricula:
                    messages.success(request, 'Compra confirmada. Seu curso está disponível!')
                    return redirect('aprendizagem:curso', matricula.pk)
                messages.warning(request, aviso)
            cupom, valor = cotar(curso, form.cleaned_data['cupom'])
        except ValidationError as exc:
            form.add_error(None, exc)
    # Toda oferta exibida possui valor e desconto assinados pelo servidor.
    assinatura = assinar_oferta(request.user, curso, cupom, valor)
    form.initial['oferta'] = assinatura
    if form.is_bound:
        dados = form.data.copy()
        dados['oferta'] = assinatura
        form.data = dados
    pendente = SolicitacaoPagamento.objects.filter(aluno=request.user, curso=curso, estado='pendente').first()
    return render(request, 'compras/checkout.html', {
        'curso': curso, 'form': form, 'valor': valor, 'cupom': cupom,
        'desconto': curso.preco - valor, 'pendente': pendente,
    })


@login_required
@require_POST
def consultar(request, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoPagamento, pk=solicitacao_id, aluno=request.user)
    matricula, aviso = consultar_pagamento(aluno=request.user, solicitacao_id=solicitacao.pk)
    if matricula:
        messages.success(request, 'Pagamento autorizado e matrícula liberada.')
        return redirect('aprendizagem:curso', matricula.pk)
    messages.info(request, aviso)
    return redirect('compras:checkout', solicitacao.curso_id)
