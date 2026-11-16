from datetime import datetime, time, timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from app.aprendizagem.models import Matricula

from .models import ResumoSemanal


def ultimo_fechamento(agora=None):
    agora = timezone.localtime(agora or timezone.now())
    domingo = agora.date() - timedelta(days=(agora.weekday() + 1) % 7)
    fechamento = timezone.make_aware(datetime.combine(domingo, time(18)))
    if fechamento > agora:
        fechamento -= timedelta(days=7)
    return fechamento


@transaction.atomic
def enviar_resumo(matricula_id, fechamento):
    matricula = Matricula.objects.select_for_update().select_related('compra__aluno', 'compra__curso').get(pk=matricula_id)
    if matricula.concluida_em or matricula.liberada_em > fechamento:
        return False
    if matricula.resumos.filter(fechamento=fechamento).exists():
        return False
    anterior = matricula.resumos.order_by('-fechamento').first()
    inicio = anterior.fechamento if anterior else matricula.liberada_em
    if fechamento <= inicio:
        return False
    concluidas = matricula.conclusoes.filter(concluida_em__gt=inicio, concluida_em__lte=fechamento)
    titulos = list(concluidas.select_related('aula').values_list('aula__titulo', flat=True))
    acumulado = matricula.conclusoes.filter(concluida_em__lte=fechamento).count()
    progresso = round(acumulado * 100 / matricula.total_aulas) if matricula.total_aulas else 0
    curso = matricula.compra.curso
    conteudo = (
        f'Olá, {matricula.compra.aluno.nome}!\n\n'
        f'Seu resumo de {curso.titulo}\n'
        f'Aulas concluídas no período de {timezone.localtime(inicio):%d/%m/%Y %Hh%M} '
        f'a {timezone.localtime(fechamento):%d/%m/%Y %Hh%M}\n'
        + '\n'.join(f'- {titulo}' for titulo in titulos)
        + f'\n\nProgresso acumulado de {progresso}% ({acumulado}/{matricula.total_aulas} aulas).'
    )
    send_mail(f'Seu progresso na Aprenda+ — {curso.titulo}', conteudo, settings.DEFAULT_FROM_EMAIL, [matricula.compra.aluno.email])
    ResumoSemanal.objects.create(matricula=matricula, fechamento=fechamento, conteudo=conteudo)
    return True


def enviar_resumos_pendentes(agora=None):
    fechamento = ultimo_fechamento(agora)
    matriculas = Matricula.objects.filter(concluida_em__isnull=True, liberada_em__lte=fechamento)
    enviados = 0
    for matricula_id in matriculas.values_list('pk', flat=True):
        enviados += enviar_resumo(matricula_id, fechamento)
    return enviados
