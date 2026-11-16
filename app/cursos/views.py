from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from app.aprendizagem.models import Matricula
from app.contas.decorators import instrutor_required
from app.notificacoes.models import AvisoConclusao

from .forms import AulaTextoForm, AulaVideoForm, CursoForm, ModuloForm, QuestionarioForm
from .models import Aula, Curso, Modulo
from .services import alternar_publicacao


def catalogo(request):
    cursos = Curso.objects.filter(publicado=True).select_related('instrutor')
    busca = request.GET.get('q', '').strip()
    if busca:
        cursos = cursos.filter(Q(titulo__icontains=busca) | Q(descricao__icontains=busca))
    return render(request, 'cursos/catalogo.html', {'cursos': cursos, 'busca': busca})


def detalhe(request, curso_id):
    curso = get_object_or_404(Curso.objects.select_related('instrutor'), pk=curso_id, publicado=True)
    matricula = None
    if request.user.is_authenticated:
        matricula = Matricula.objects.filter(compra__curso=curso, compra__aluno=request.user).first()
    return render(request, 'cursos/detalhe.html', {
        'curso': curso, 'modulos': curso.modulos.prefetch_related('aulas'), 'matricula': matricula,
    })


def cursos_do_instrutor(usuario):
    cursos = Curso.objects.all()
    return cursos if usuario.is_superuser else cursos.filter(instrutor=usuario)


@instrutor_required
def painel_instrutor(request):
    avisos = AvisoConclusao.objects.select_related('matricula__compra__curso', 'matricula__compra__aluno')
    if not request.user.is_superuser:
        avisos = avisos.filter(matricula__compra__curso__instrutor=request.user)
    return render(request, 'instrutor/painel.html', {
        'cursos': cursos_do_instrutor(request.user), 'avisos': avisos,
    })


@instrutor_required
@transaction.atomic
def editar_curso(request, curso_id=None):
    curso = get_object_or_404(cursos_do_instrutor(request.user), pk=curso_id) if curso_id else Curso(instrutor=request.user)
    form = CursoForm(request.POST if request.method == 'POST' else None, instance=curso)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Curso salvo.')
        return redirect('instrutor:gerenciar', curso.pk)
    return render(request, 'instrutor/form.html', {'form': form, 'titulo': 'Editar curso' if curso_id else 'Criar curso'})


@instrutor_required
def gerenciar(request, curso_id):
    curso = get_object_or_404(cursos_do_instrutor(request.user), pk=curso_id)
    return render(request, 'instrutor/curso.html', {'curso': curso, 'modulos': curso.modulos.prefetch_related('aulas')})


@instrutor_required
@require_POST
def publicar(request, curso_id):
    curso = get_object_or_404(cursos_do_instrutor(request.user), pk=curso_id)
    try:
        curso = alternar_publicacao(curso.pk)
        messages.success(request, 'Curso publicado.' if curso.publicado else 'Curso despublicado.')
    except ValidationError as exc:
        messages.error(request, ' '.join(exc.messages))
    return redirect('instrutor:gerenciar', curso.pk)


@instrutor_required
@transaction.atomic
def editar_modulo(request, curso_id, modulo_id=None):
    curso = get_object_or_404(cursos_do_instrutor(request.user), pk=curso_id)
    modulo = get_object_or_404(Modulo, pk=modulo_id, curso=curso) if modulo_id else Modulo(curso=curso)
    if curso.estrutura_bloqueada:
        messages.error(request, 'A estrutura do curso fica fixa após a primeira compra confirmada.')
        return redirect('instrutor:gerenciar', curso.pk)
    form = ModuloForm(request.POST if request.method == 'POST' else None, instance=modulo)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Módulo salvo.')
        return redirect('instrutor:gerenciar', curso.pk)
    return render(request, 'instrutor/form.html', {'form': form, 'titulo': 'Editar módulo' if modulo_id else 'Criar módulo', 'curso': curso})


@instrutor_required
@transaction.atomic
def editar_aula(request, modulo_id, tipo=None, aula_id=None):
    modulo = get_object_or_404(Modulo.objects.select_related('curso'), pk=modulo_id, curso__in=cursos_do_instrutor(request.user))
    if modulo.curso.estrutura_bloqueada:
        messages.error(request, 'A estrutura do curso fica fixa após a primeira compra confirmada.')
        return redirect('instrutor:gerenciar', modulo.curso_id)
    aula = get_object_or_404(Aula, pk=aula_id, modulo=modulo).conteudo if aula_id else None
    tipo = aula.tipo if aula else tipo
    formularios = {'video': AulaVideoForm, 'texto': AulaTextoForm, 'questionario': QuestionarioForm}
    if tipo not in formularios:
        raise Http404('Tipo de aula inválido.')
    formulario = formularios[tipo]
    if aula is None:
        aula = formulario._meta.model(modulo=modulo, tipo=tipo)
    form = formulario(request.POST if request.method == 'POST' else None, instance=aula)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Aula salva.')
        return redirect('instrutor:gerenciar', modulo.curso_id)
    return render(request, 'instrutor/form.html', {
        'form': form, 'titulo': 'Editar aula' if aula_id else f'Criar aula de {aula.get_tipo_display().lower()}',
        'curso': modulo.curso,
    })


@instrutor_required
@transaction.atomic
def excluir(request, curso_id, modulo_id=None, aula_id=None):
    curso = get_object_or_404(cursos_do_instrutor(request.user), pk=curso_id)
    objeto = curso
    if modulo_id:
        objeto = get_object_or_404(Modulo, pk=modulo_id, curso=curso)
    if aula_id:
        objeto = get_object_or_404(Aula, pk=aula_id, modulo__curso=curso).conteudo
    if request.method == 'POST':
        try:
            objeto.delete()
            messages.success(request, 'Exclusão realizada.')
        except ValidationError as exc:
            messages.error(request, ' '.join(exc.messages))
            return redirect('instrutor:gerenciar', curso.pk)
        return redirect('instrutor:painel_instrutor') if objeto is curso else redirect('instrutor:gerenciar', curso.pk)
    return render(request, 'instrutor/excluir.html', {'objeto': objeto, 'curso': curso})


@login_required
@require_POST
def ler_aviso(request, aviso_id):
    avisos = AvisoConclusao.objects.all()
    if not request.user.is_superuser:
        avisos = avisos.filter(matricula__compra__curso__instrutor=request.user)
    aviso = get_object_or_404(avisos, pk=aviso_id)
    aviso.lido_em = timezone.now()
    aviso.save(update_fields=['lido_em'])
    return redirect('instrutor:painel_instrutor')
