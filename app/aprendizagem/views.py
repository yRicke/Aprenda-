from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from app.cursos.models import Aula

from .forms import RespostasForm
from .models import Certificado, Matricula
from .selectors import dados_do_painel, primeira_aula_pendente
from .services import concluir_aula, concluir_curso, responder


def buscar_matricula(usuario, matricula_id):
    return get_object_or_404(
        Matricula.objects.select_related('compra__curso', 'compra__aluno'),
        pk=matricula_id, compra__aluno=usuario,
    )


@login_required
def painel(request):
    contexto = dados_do_painel(request.user, request.GET.get('status', 'todos'))
    return render(request, 'aprendizagem/painel.html', contexto)


@login_required
def curso(request, matricula_id):
    matricula = buscar_matricula(request.user, matricula_id)
    modulos = matricula.compra.curso.modulos.prefetch_related('aulas')
    concluidas = set(matricula.conclusoes.values_list('aula_id', flat=True))
    return render(request, 'aprendizagem/curso.html', {
        'matricula': matricula, 'modulos': modulos, 'concluidas': concluidas,
        'aula_retomada': primeira_aula_pendente(matricula),
    })


@login_required
def aula(request, matricula_id, aula_id):
    matricula = buscar_matricula(request.user, matricula_id)
    aula = get_object_or_404(Aula, pk=aula_id, modulo__curso=matricula.compra.curso)
    conteudo = aula.conteudo
    aulas = list(Aula.objects.filter(modulo__curso=matricula.compra.curso).select_related('modulo'))
    posicao = aulas.index(aula)
    anterior = aulas[posicao - 1] if posicao else None
    proxima = aulas[posicao + 1] if posicao + 1 < len(aulas) else None
    concluidas = set(matricula.conclusoes.values_list('aula_id', flat=True))
    form = None
    if aula.tipo == Aula.Tipo.QUESTIONARIO:
        form = RespostasForm(conteudo.questoes, request.POST if request.method == 'POST' else None)
        if request.method == 'POST' and form.is_valid():
            try:
                tentativa = responder(
                    matricula_id=matricula.pk, aluno=request.user,
                    questionario=conteudo, respostas=form.respostas,
                )
                messages.success(request, f'Tentativa registrada. Sua nota foi {tentativa.nota}/10.')
                return redirect('aprendizagem:aula', matricula.pk, aula.pk)
            except ValidationError as exc:
                form.add_error(None, exc)
    elif request.method == 'POST':
        concluir_aula(matricula_id=matricula.pk, aluno=request.user, aula=aula)
        messages.success(request, 'Aula concluída!')
        if request.POST.get('continuar') == '1' and proxima:
            return redirect('aprendizagem:aula', matricula.pk, proxima.pk)
        return redirect('aprendizagem:curso', matricula.pk)
    return render(request, 'aprendizagem/aula.html', {
        'matricula': matricula, 'aula': aula, 'conteudo': conteudo, 'form': form,
        'concluida': matricula.conclusoes.filter(aula=aula).exists(),
        'tentativas': matricula.tentativas.filter(questionario_id=aula.pk),
        'aulas': aulas, 'concluidas': concluidas,
        'anterior': anterior, 'proxima': proxima, 'numero_aula': posicao + 1,
    })


@login_required
@require_POST
def concluir(request, matricula_id):
    matricula = buscar_matricula(request.user, matricula_id)
    try:
        certificado = concluir_curso(matricula_id=matricula.pk, aluno=request.user)
    except ValidationError as exc:
        messages.warning(request, ' '.join(exc.messages))
        return redirect('aprendizagem:curso', matricula.pk)
    return redirect('aprendizagem:certificado', certificado.codigo)


@login_required
def certificado(request, codigo):
    certificado = get_object_or_404(
        Certificado.objects.select_related('matricula__compra__aluno', 'matricula__compra__curso'),
        codigo=codigo, matricula__compra__aluno=request.user,
    )
    return render(request, 'aprendizagem/certificado.html', {'certificado': certificado})
