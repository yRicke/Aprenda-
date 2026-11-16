from datetime import timedelta

from django.db.models import Count, F, Max
from django.utils import timezone

from app.cursos.models import Aula

from .models import ConclusaoAula, Matricula


def primeira_aula_pendente(matricula):
    return Aula.objects.filter(modulo__curso_id=matricula.compra.curso_id).exclude(
        pk__in=matricula.conclusoes.values('aula_id'),
    ).select_related('modulo').first()


def dados_do_painel(aluno, filtro='todos'):
    matriculas = list(Matricula.objects.filter(compra__aluno=aluno).select_related(
        'compra__curso__instrutor', 'certificado',
    ).annotate(
        ultima_atividade=Max('conclusoes__concluida_em'),
        aulas_feitas=Count('conclusoes'),
    ).order_by(F('ultima_atividade').desc(nulls_last=True), '-liberada_em'))
    andamento = [matricula for matricula in matriculas if not matricula.concluida_em]
    concluidos = [matricula for matricula in matriculas if matricula.concluida_em]
    filtros = {'todos': matriculas, 'andamento': andamento, 'concluidos': concluidos}
    if filtro not in filtros:
        filtro = 'todos'

    hoje = timezone.localdate()
    inicio = hoje - timedelta(days=hoje.weekday())
    atividade = ConclusaoAula.objects.filter(
        matricula__compra__aluno=aluno, concluida_em__date__range=(inicio, hoje),
    ).values('concluida_em__date').annotate(total=Count('pk'))
    contagens = {item['concluida_em__date']: item['total'] for item in atividade}
    semana = []
    for indice in range(7):
        dia = inicio + timedelta(days=indice)
        semana.append({'data': dia, 'aulas': contagens.get(dia, 0), 'hoje': dia == hoje})

    retomada = andamento[0] if andamento else None
    return {
        'matriculas': filtros[filtro], 'total_matriculas': len(matriculas), 'filtro': filtro,
        'total_andamento': len(andamento), 'total_concluidos': len(concluidos),
        'total_aulas_feitas': sum(matricula.aulas_feitas for matricula in matriculas),
        'retomada': retomada,
        'aula_retomada': primeira_aula_pendente(retomada) if retomada else None,
        'semana': semana, 'aulas_semana': sum(contagens.values()),
    }
