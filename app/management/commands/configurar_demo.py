from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from app.compras.models import Cupom
from app.contas.models import Usuario
from app.cursos.models import AulaTexto, AulaVideo, Curso, Modulo, Questionario


class Command(BaseCommand):
    help = 'Cria o administrador admin/admin e um curso demonstrativo. Pode ser repetido.'

    @transaction.atomic
    def handle(self, *args, **options):
        admin, criado = Usuario.objects.get_or_create(username='admin', defaults={
            'email': 'admin@aprenda.local', 'first_name': 'Administrador',
            'perfil': Usuario.Perfil.INSTRUTOR, 'is_staff': True, 'is_superuser': True,
        })
        if criado:
            admin.set_password('admin')
            admin.save()
            self.stdout.write('Administrador criado. Usuário admin e senha admin.')
        else:
            self.stdout.write('O usuário admin já existe. Os dados atuais foram preservados.')
        Cupom.objects.get_or_create(codigo='APRENDA10', defaults={
            'percentual': Decimal('10'), 'valido_ate': timezone.now() + timedelta(days=365),
        })
        if not Curso.objects.filter(instrutor=admin, titulo='Introdução à programação com Python').exists():
            curso = Curso.objects.create(
                instrutor=admin, titulo='Introdução à programação com Python', preco=Decimal('99.90'),
                descricao='Dê os primeiros passos na programação. Conheça variáveis, funções e pratique com um questionário.',
            )
            modulo = Modulo.objects.create(curso=curso, titulo='Primeiros passos', ordem=1)
            AulaTexto.objects.create(
                modulo=modulo, titulo='Variáveis e funções', ordem=1,
                texto='Uma variável associa um nome a um valor.\n\nnome = "Aprenda+"\nprint(nome)\n\n'
                'Uma função agrupa instruções para reutilizar uma tarefa. Em Python usamos def para definir funções.\n\n'
                'def saudacao(nome):\n    return "Olá, " + nome\n\nTente criar sua própria função!',
            )
            AulaVideo.objects.create(
                modulo=modulo, titulo='Conhecendo a linguagem', ordem=2, duracao_segundos=120,
                url_video='https://www.youtube.com/watch?v=rfscVS0vtbw',
            )
            Questionario.objects.create(modulo=modulo, titulo='Revise seus conhecimentos', ordem=3, questoes=[
                {'enunciado': 'Qual palavra define uma função em Python?', 'opcoes': ['def', 'function', 'func'], 'correta': 0},
                {'enunciado': 'O que print faz?', 'opcoes': ['Exibe um valor', 'Cria uma variável'], 'correta': 0},
            ])
            curso.publicado = True
            curso.save(update_fields=['publicado'])
            self.stdout.write('Curso demonstrativo publicado.')
        self.stdout.write(self.style.SUCCESS('Configuração concluída. Cupom de demonstração APRENDA10.'))
