from decimal import Decimal

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.module_loading import import_string

from app.aprendizagem.models import Matricula
from app.cursos.models import Curso

from .models import Compra, Cupom, Pagamento, SolicitacaoPagamento


def cotar(curso, codigo=''):
    cupom = None
    if codigo.strip():
        cupom = Cupom.objects.filter(codigo__iexact=codigo.strip()).first()
        if cupom is None or not cupom.validar():
            raise ValidationError('Cupom inválido ou vencido.')
    desconto = cupom.calcular_desconto(curso.preco) if cupom else Decimal('0.00')
    return cupom, curso.preco - desconto


def assinar_oferta(aluno, curso, cupom, valor):
    return signing.dumps({
        'aluno': aluno.pk, 'curso': curso.pk, 'cupom': cupom.codigo if cupom else '',
        'valor': str(valor), 'preco': str(curso.preco),
    }, salt='oferta-curso')


@transaction.atomic
def comprar(*, aluno, curso_id, oferta, token):
    curso = Curso.objects.select_for_update().get(pk=curso_id)
    existente = Matricula.objects.filter(compra__aluno=aluno, compra__curso=curso).first()
    if existente:
        return existente, ''
    if not curso.publicado:
        raise ValidationError('Este curso está indisponível para compra.')
    if SolicitacaoPagamento.objects.filter(aluno=aluno, curso=curso, estado='pendente').exists():
        raise ValidationError('Consulte o pagamento pendente antes de iniciar outra compra.')
    try:
        dados = signing.loads(oferta, salt='oferta-curso', max_age=1800)
    except signing.BadSignature as exc:
        raise ValidationError('A oferta expirou. Confira o valor novamente.') from exc
    if dados['aluno'] != aluno.pk or dados['curso'] != curso.pk:
        raise ValidationError('Oferta inválida para esta compra.')
    cupom, valor = cotar(curso, dados['cupom'])
    if dados['valor'] != str(valor) or dados['preco'] != str(curso.preco):
        raise ValidationError('O preço mudou. Confira a nova oferta antes de confirmar.')

    solicitacao = SolicitacaoPagamento.objects.create(aluno=aluno, curso=curso, cupom=cupom, valor=valor)
    operadora = import_string(settings.PAYMENT_GATEWAY)()
    try:
        resultado = operadora.autorizar(valor=valor, token=token, chave=solicitacao.chave)
    except TimeoutError:
        return None, 'Pagamento sem resposta. Consulte o estado antes de tentar novamente.'
    return registrar_resultado(solicitacao, resultado)


def registrar_resultado(solicitacao, resultado):
    solicitacao.estado = resultado.estado
    solicitacao.save(update_fields=['estado'])
    if resultado.estado == 'recusado':
        return None, 'Pagamento recusado. A matrícula será liberada após uma compra autorizada.'
    if resultado.estado == 'pendente':
        return None, 'Pagamento sem resposta. Consulte o estado antes de tentar novamente.'
    compra = Compra.objects.create(
        aluno=solicitacao.aluno, curso=solicitacao.curso,
        cupom=solicitacao.cupom, valor_final=solicitacao.valor,
    )
    Pagamento.objects.create(compra=compra, solicitacao=solicitacao, referencia=resultado.referencia)
    return Matricula.objects.create(compra=compra), ''


@transaction.atomic
def consultar_pagamento(*, aluno, solicitacao_id):
    solicitacao = SolicitacaoPagamento.objects.select_for_update().get(pk=solicitacao_id, aluno=aluno)
    if solicitacao.estado != 'pendente':
        return None, 'O pagamento já foi consultado.'
    operadora = import_string(settings.PAYMENT_GATEWAY)()
    resultado = operadora.consultar(chave=solicitacao.chave)
    return registrar_resultado(solicitacao, resultado)
