from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from app.cursos.models import Aula, Questionario
from app.notificacoes.models import AvisoConclusao

from .models import Certificado, ConclusaoAula, Matricula, TentativaQuestionario


def validar_acesso(matricula, aluno, aula=None):
    if matricula.compra.aluno_id != aluno.pk:
        raise PermissionDenied
    if aula and aula.modulo.curso_id != matricula.compra.curso_id:
        raise ValidationError('Esta aula pertence a outro curso.')


@transaction.atomic
def concluir_aula(*, matricula_id, aluno, aula):
    matricula = Matricula.objects.select_for_update().select_related('compra').get(pk=matricula_id)
    validar_acesso(matricula, aluno, aula)
    if aula.tipo == Aula.Tipo.QUESTIONARIO:
        raise ValidationError('Envie as respostas para concluir o questionário.')
    return ConclusaoAula.objects.get_or_create(matricula=matricula, aula=aula)[0]


@transaction.atomic
def responder(*, matricula_id, aluno, questionario, respostas):
    matricula = Matricula.objects.select_for_update().select_related('compra').get(pk=matricula_id)
    validar_acesso(matricula, aluno, questionario)
    if not isinstance(questionario, Questionario):
        raise ValidationError('Selecione um questionário.')
    if matricula.concluida_em:
        raise ValidationError('A matrícula já foi concluída. Consulte o histórico de tentativas.')
    if len(respostas) != len(questionario.questoes):
        raise ValidationError('Responda todas as questões.')
    for resposta, questao in zip(respostas, questionario.questoes):
        if type(resposta) is not int or not 0 <= resposta < len(questao['opcoes']):
            raise ValidationError('Uma das respostas é inválida.')
    acertos = sum(resposta == questao['correta'] for resposta, questao in zip(respostas, questionario.questoes))
    nota = (Decimal(acertos) * 10 / len(respostas)).quantize(Decimal('0.01'))
    tentativa = TentativaQuestionario.objects.create(
        matricula=matricula, questionario=questionario, respostas=respostas, nota=nota,
    )
    ConclusaoAula.objects.get_or_create(matricula=matricula, aula=questionario)
    return tentativa


@transaction.atomic
def concluir_curso(*, matricula_id, aluno):
    matricula = Matricula.objects.select_for_update().select_related('compra').get(pk=matricula_id)
    validar_acesso(matricula, aluno)
    if matricula.concluida_em:
        return matricula.certificado
    pendentes = matricula.pendencias
    if pendentes or not matricula.total_aulas:
        raise ValidationError(f'Você ainda tem {pendentes} aula(s) pendente(s). Continue seus estudos.')
    # As duas saídas ficam disponíveis juntas, sem efeito parcial após uma falha.
    certificado = Certificado.objects.create(matricula=matricula)
    AvisoConclusao.objects.create(matricula=matricula)
    matricula.concluida_em = timezone.now()
    matricula.save(update_fields=['concluida_em'])
    return certificado
