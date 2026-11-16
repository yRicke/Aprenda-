from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import authenticate
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from app.aprendizagem.models import Certificado, ConclusaoAula, Matricula
from app.aprendizagem.services import concluir_aula, concluir_curso, responder
from app.compras.models import Compra, Cupom, Pagamento, SolicitacaoPagamento
from app.compras.services import assinar_oferta, comprar, consultar_pagamento, cotar
from app.contas.models import Usuario
from app.cursos.models import AulaTexto, AulaVideo, Curso, Modulo, Questionario
from app.notificacoes.models import AvisoConclusao, ResumoSemanal
from app.notificacoes.services import enviar_resumos_pendentes, ultimo_fechamento


class PlataformaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.instrutor = Usuario.objects.create_user('instrutor', 'instrutor@example.com', 'teste-forte123', perfil='instrutor')
        cls.aluno = Usuario.objects.create_user('aluno', 'aluno@example.com', 'teste-forte123')
        cls.outro = Usuario.objects.create_user('outro', 'outro@example.com', 'teste-forte123')
        cls.curso = Curso.objects.create(instrutor=cls.instrutor, titulo='Python', descricao='Curso de Python', preco='100.00')
        cls.modulo = Modulo.objects.create(curso=cls.curso, titulo='Introdução', ordem=1)
        cls.texto = AulaTexto.objects.create(modulo=cls.modulo, titulo='Texto', ordem=1, texto='Conteúdo da aula')
        cls.video = AulaVideo.objects.create(modulo=cls.modulo, titulo='Vídeo', ordem=2, url_video='https://youtu.be/teste')
        cls.quiz = Questionario.objects.create(modulo=cls.modulo, titulo='Questionário', ordem=3, questoes=[
            {'enunciado': 'Qual linguagem?', 'opcoes': ['Python', 'Java'], 'correta': 0},
        ])
        cls.curso.publicado = True
        cls.curso.save()
        cls.cupom = Cupom.objects.create(codigo='DEZ', percentual=10, valido_ate=timezone.now() + timedelta(days=1))

    def comprar_curso(self, aluno=None, codigo='', token='aprovar'):
        aluno = aluno or self.aluno
        cupom, valor = cotar(self.curso, codigo)
        return comprar(aluno=aluno, curso_id=self.curso.pk, token=token,
                       oferta=assinar_oferta(aluno, self.curso, cupom, valor))

    def concluir_todas(self, matricula):
        concluir_aula(matricula_id=matricula.pk, aluno=self.aluno, aula=self.texto)
        concluir_aula(matricula_id=matricula.pk, aluno=self.aluno, aula=self.video)
        responder(matricula_id=matricula.pk, aluno=self.aluno, questionario=self.quiz, respostas=[1])

    def test_compra_autorizada_com_desconto_e_repeticao(self):
        matricula, _ = self.comprar_curso(codigo='dez')
        self.assertEqual(matricula.compra.valor_final, Decimal('90.00'))
        self.assertEqual(self.comprar_curso()[0].pk, matricula.pk)
        self.assertEqual(Compra.objects.count(), 1)
        self.assertEqual(Pagamento.objects.count(), 1)
        self.assertEqual(Matricula.objects.count(), 1)

    def test_pagamento_recusado(self):
        matricula, aviso = self.comprar_curso(token='recusar')
        self.assertIsNone(matricula)
        self.assertIn('recusado', aviso)
        self.assertFalse(Compra.objects.exists())
        self.assertFalse(Matricula.objects.exists())

    def test_timeout_exige_consulta_antes_de_nova_compra(self):
        self.assertIsNone(self.comprar_curso(token='sem_resposta')[0])
        with self.assertRaises(ValidationError):
            self.comprar_curso()
        self.assertEqual(SolicitacaoPagamento.objects.count(), 1)
        pendente = SolicitacaoPagamento.objects.get()
        consultar_pagamento(aluno=self.aluno, solicitacao_id=pendente.pk)
        self.assertIsNotNone(self.comprar_curso()[0])

    def test_oferta_adulterada_ou_de_outro_aluno(self):
        oferta = assinar_oferta(self.outro, self.curso, None, self.curso.preco)
        for assinatura in (oferta, 'invalida'):
            with self.assertRaises(ValidationError):
                comprar(aluno=self.aluno, curso_id=self.curso.pk, oferta=assinatura, token='aprovar')
        self.assertFalse(SolicitacaoPagamento.objects.exists())

    def test_cupom_expirado_ou_preco_alterado_exige_nova_oferta(self):
        oferta = assinar_oferta(self.aluno, self.curso, self.cupom, Decimal('90.00'))
        self.cupom.valido_ate = timezone.now() - timedelta(seconds=1)
        self.cupom.save()
        with self.assertRaises(ValidationError):
            comprar(aluno=self.aluno, curso_id=self.curso.pk, oferta=oferta, token='aprovar')
        oferta = assinar_oferta(self.aluno, self.curso, None, self.curso.preco)
        self.curso.preco = Decimal('150.00')
        self.curso.save()
        with self.assertRaises(ValidationError):
            comprar(aluno=self.aluno, curso_id=self.curso.pk, oferta=oferta, token='aprovar')

    def test_publicacao_exige_modulos_com_aulas(self):
        curso = Curso.objects.create(instrutor=self.instrutor, titulo='Vazio', descricao='Descrição', preco=0)
        curso.publicado = True
        with self.assertRaises(ValidationError):
            curso.save()
        curso.publicado = False
        Modulo.objects.create(curso=curso, titulo='Módulo vazio', ordem=1)
        curso.publicado = True
        with self.assertRaises(ValidationError):
            curso.save()

    def test_conclusao_de_aula_unica_e_questionario_com_historico(self):
        matricula, _ = self.comprar_curso()
        for _ in range(2):
            concluir_aula(matricula_id=matricula.pk, aluno=self.aluno, aula=self.texto)
        self.assertEqual(matricula.conclusoes.count(), 1)
        primeira = responder(matricula_id=matricula.pk, aluno=self.aluno, questionario=self.quiz, respostas=[1])
        segunda = responder(matricula_id=matricula.pk, aluno=self.aluno, questionario=self.quiz, respostas=[0])
        self.assertEqual(primeira.nota, 0)
        self.assertEqual(segunda.nota, 10)
        self.assertEqual(matricula.tentativas.count(), 2)
        self.assertEqual(matricula.conclusoes.count(), 2)

    def test_respostas_invalidas_preservam_progresso(self):
        matricula, _ = self.comprar_curso()
        for respostas in ([], [2], ['0'], [True]):
            with self.assertRaises(ValidationError):
                responder(matricula_id=matricula.pk, aluno=self.aluno, questionario=self.quiz, respostas=respostas)
        with self.assertRaises(ValidationError):
            concluir_aula(matricula_id=matricula.pk, aluno=self.aluno, aula=self.quiz)
        self.assertFalse(matricula.conclusoes.exists())
        self.assertFalse(matricula.tentativas.exists())

    def test_conclusao_incompleta_sem_certificado_ou_aviso(self):
        matricula, _ = self.comprar_curso()
        with self.assertRaisesMessage(ValidationError, '3 aula(s)'):
            concluir_curso(matricula_id=matricula.pk, aluno=self.aluno)
        self.assertFalse(Certificado.objects.exists())
        self.assertFalse(AvisoConclusao.objects.exists())

    def test_certificado_aviso_e_matricula_finalizados_uma_vez(self):
        matricula, _ = self.comprar_curso()
        self.concluir_todas(matricula)
        certificado = concluir_curso(matricula_id=matricula.pk, aluno=self.aluno)
        repetido = concluir_curso(matricula_id=matricula.pk, aluno=self.aluno)
        matricula.refresh_from_db()
        self.assertEqual(repetido.pk, certificado.pk)
        self.assertEqual(matricula.progresso, 100)
        self.assertIsNotNone(matricula.concluida_em)
        self.assertEqual(AvisoConclusao.objects.count(), 1)

    def test_falha_no_aviso_desfaz_emissao_e_finalizacao(self):
        matricula, _ = self.comprar_curso()
        self.concluir_todas(matricula)
        with patch('app.aprendizagem.services.AvisoConclusao.objects.create', side_effect=RuntimeError('falha')):
            with self.assertRaises(RuntimeError):
                concluir_curso(matricula_id=matricula.pk, aluno=self.aluno)
        matricula.refresh_from_db()
        self.assertIsNone(matricula.concluida_em)
        self.assertFalse(Certificado.objects.exists())

    def test_estrutura_fixa_apos_compra(self):
        self.comprar_curso()
        for objeto in (self.curso, self.modulo, self.texto, self.video, self.quiz):
            with self.assertRaises(ValidationError):
                objeto.delete()
        self.texto.texto = 'Outro texto'
        with self.assertRaises(ValidationError):
            self.texto.save()
        with self.assertRaises(ValidationError):
            AulaTexto.objects.create(modulo=self.modulo, titulo='Nova', ordem=4, texto='Novo')

    def test_exclusao_em_cascata_antes_da_compra(self):
        self.curso.delete()
        self.assertFalse(Modulo.objects.exists())
        self.assertFalse(AulaTexto.objects.exists())
        self.assertFalse(Questionario.objects.exists())

    def test_autorizacao_em_rotas_de_aluno_e_instrutor(self):
        matricula, _ = self.comprar_curso()
        self.client.force_login(self.outro)
        self.assertEqual(self.client.get(reverse('aprendizagem:curso', args=[matricula.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('aprendizagem:aula', args=[matricula.pk, self.texto.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('instrutor:painel_instrutor')).status_code, 403)
        outro_instrutor = Usuario.objects.create_user('instrutor2', 'i2@example.com', perfil='instrutor')
        self.client.force_login(outro_instrutor)
        self.assertEqual(self.client.get(reverse('instrutor:gerenciar', args=[self.curso.pk])).status_code, 404)

    def test_jornada_http_completa(self):
        self.client.force_login(self.aluno)
        self.assertEqual(self.client.get(reverse('cursos:catalogo')).status_code, 200)
        url = reverse('compras:checkout', args=[self.curso.pk])
        resposta = self.client.post(url, {'acao': 'aplicar', 'cupom': 'DEZ', 'token': 'aprovar'})
        oferta = resposta.context['form']['oferta'].value()
        resposta = self.client.post(url, {'acao': 'comprar', 'oferta': oferta, 'cupom': 'DEZ', 'token': 'aprovar'}, follow=True)
        self.assertEqual(resposta.status_code, 200)
        matricula = Matricula.objects.get()
        for aula in (self.texto, self.video):
            url = reverse('aprendizagem:aula', args=[matricula.pk, aula.pk])
            self.assertEqual(self.client.get(url).status_code, 200)
            self.assertEqual(self.client.post(url).status_code, 302)
        resposta = self.client.post(reverse('aprendizagem:aula', args=[matricula.pk, self.quiz.pk]), {'questao_0': '1'}, follow=True)
        self.assertContains(resposta, '0,00/10')
        resposta = self.client.post(reverse('aprendizagem:concluir', args=[matricula.pk]), follow=True)
        self.assertContains(resposta, 'Certificado de conclusão')
        self.client.force_login(self.instrutor)
        self.assertContains(self.client.get(reverse('instrutor:painel_instrutor')), 'aluno')

    def test_formularios_instrutor_e_ordem_duplicada(self):
        self.client.force_login(self.instrutor)
        for nome, argumentos in (
            ('instrutor:editar', [self.curso.pk]),
            ('instrutor:modulo_editar', [self.curso.pk, self.modulo.pk]),
            ('instrutor:aula_editar', [self.modulo.pk, self.texto.pk]),
            ('instrutor:aula_editar', [self.modulo.pk, self.video.pk]),
            ('instrutor:aula_editar', [self.modulo.pk, self.quiz.pk]),
        ):
            self.assertEqual(self.client.get(reverse(nome, args=argumentos)).status_code, 200)
        resposta = self.client.post(reverse('instrutor:aula_criar', args=[self.modulo.pk, 'texto']), {
            'titulo': 'Duplicada', 'ordem': 1, 'texto': 'Conteúdo',
        })
        self.assertContains(resposta, 'Já existe uma aula nesta ordem.')

    def test_criacao_de_curso_modulo_aulas_e_publicacao_por_http(self):
        self.client.force_login(self.instrutor)
        self.client.post(reverse('instrutor:criar'), {'titulo': 'Novo curso', 'descricao': 'Descrição', 'preco': '20.00'})
        curso = Curso.objects.get(titulo='Novo curso')
        self.client.post(reverse('instrutor:modulo_criar', args=[curso.pk]), {'titulo': 'Módulo novo', 'ordem': 1})
        modulo = curso.modulos.get()
        self.client.post(reverse('instrutor:aula_criar', args=[modulo.pk, 'texto']), {
            'titulo': 'Nova aula', 'ordem': 1, 'texto': 'Texto da aula',
        })
        self.assertEqual(modulo.aulas.count(), 1)
        self.client.post(reverse('instrutor:publicar', args=[curso.pk]))
        curso.refresh_from_db()
        self.assertTrue(curso.publicado)

    def test_edicao_dos_tipos_de_aula_por_http(self):
        self.client.force_login(self.instrutor)
        for aula, campos in (
            (self.texto, {'texto': 'Texto atualizado'}),
            (self.video, {'url_video': 'https://youtu.be/novo', 'duracao_segundos': 10}),
            (self.quiz, {'questoes': '[{"enunciado":"Nova pergunta?","opcoes":["Sim","Não"],"correta":1}]'}),
        ):
            resposta = self.client.post(reverse('instrutor:aula_editar', args=[self.modulo.pk, aula.pk]), {
                'titulo': 'Título atualizado', 'ordem': aula.ordem, **campos,
            })
            self.assertEqual(resposta.status_code, 302)
            aula.refresh_from_db()
            self.assertEqual(aula.titulo, 'Título atualizado')

    def test_curso_despublicado_preserva_acesso_do_aluno_matriculado(self):
        matricula, _ = self.comprar_curso()
        self.curso.publicado = False
        self.curso.save()
        self.client.force_login(self.aluno)
        self.assertEqual(self.client.get(reverse('aprendizagem:curso', args=[matricula.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse('cursos:detalhe', args=[self.curso.pk])).status_code, 404)
        with self.assertRaises(ValidationError):
            self.comprar_curso(aluno=self.outro)

    def test_certificado_privado_e_leitura_de_aviso(self):
        matricula, _ = self.comprar_curso()
        self.concluir_todas(matricula)
        certificado = concluir_curso(matricula_id=matricula.pk, aluno=self.aluno)
        self.client.force_login(self.outro)
        self.assertEqual(self.client.get(reverse('aprendizagem:certificado', args=[certificado.codigo])).status_code, 404)
        aviso = AvisoConclusao.objects.get()
        self.assertEqual(self.client.post(reverse('instrutor:ler_aviso', args=[aviso.pk])).status_code, 404)
        self.client.force_login(self.instrutor)
        self.assertEqual(self.client.post(reverse('instrutor:ler_aviso', args=[aviso.pk])).status_code, 302)
        aviso.refresh_from_db()
        self.assertIsNotNone(aviso.lido_em)

    def test_tentativa_de_editar_estrutura_com_compras_e_bloqueada(self):
        self.comprar_curso()
        self.client.force_login(self.instrutor)
        resposta = self.client.post(reverse('instrutor:aula_editar', args=[self.modulo.pk, self.texto.pk]), {
            'titulo': 'Adulterada', 'ordem': 1, 'texto': 'Adulterado',
        }, follow=True)
        self.assertContains(resposta, 'estrutura do curso fica fixa')
        self.texto.refresh_from_db()
        self.assertEqual(self.texto.titulo, 'Texto')

    def test_get_nao_confirma_compra_nem_conclusao(self):
        self.client.force_login(self.aluno)
        self.client.get(reverse('compras:checkout', args=[self.curso.pk]))
        self.assertFalse(Compra.objects.exists())
        matricula, _ = self.comprar_curso()
        resposta = self.client.get(reverse('aprendizagem:concluir', args=[matricula.pk]))
        self.assertEqual(resposta.status_code, 405)
        self.assertFalse(Certificado.objects.exists())

    def test_admin_preserva_estrutura_e_registros_financeiros(self):
        matricula, _ = self.comprar_curso()
        admin = Usuario.objects.create_superuser('gestor', 'gestor@example.com', 'teste-forte123')
        self.client.force_login(admin)
        self.assertEqual(self.client.get(f'/admin/compras/compra/{matricula.compra_id}/delete/').status_code, 403)
        self.assertEqual(self.client.get(f'/admin/cursos/aulatexto/{self.texto.pk}/delete/').status_code, 403)
        self.assertEqual(self.client.get(f'/admin/cursos/curso/{self.curso.pk}/delete/').status_code, 403)

    def test_cadastro_cria_usuario_com_senha_e_perfil(self):
        resposta = self.client.post(reverse('contas:cadastro'), {
            'username': 'nova', 'email': 'nova@example.com', 'perfil': 'instrutor',
            'first_name': 'Nova', 'last_name': 'Pessoa',
            'password1': 'uma-senha-forte123', 'password2': 'uma-senha-forte123',
        })
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(Usuario.objects.get(username='nova').pode_instruir)
        self.assertIsNotNone(authenticate(username='nova', password='uma-senha-forte123'))

    def test_configuracao_demo_repetivel_e_login_admin(self):
        for _ in range(2):
            call_command('configurar_demo', stdout=StringIO())
        admin = authenticate(username='admin', password='admin')
        self.assertTrue(admin.is_superuser)
        self.assertEqual(Curso.objects.filter(instrutor=admin).count(), 1)
        self.client.force_login(admin)
        self.assertEqual(self.client.get('/admin/').status_code, 200)
        admin.set_password('outra-senha-forte123')
        admin.save()
        call_command('configurar_demo', stdout=StringIO())
        self.assertIsNotNone(authenticate(username='admin', password='outra-senha-forte123'))

    @override_settings(MAILERS={'default': {'BACKEND': 'django.core.mail.backends.locmem.EmailBackend'}})
    def test_resumo_semanal_limites_e_envio_unico(self):
        matricula, _ = self.comprar_curso()
        fechamento = ultimo_fechamento()
        matricula.liberada_em = fechamento - timedelta(days=6)
        matricula.save()
        ConclusaoAula.objects.create(matricula=matricula, aula=self.texto, concluida_em=fechamento - timedelta(days=1))
        ConclusaoAula.objects.create(matricula=matricula, aula=self.video, concluida_em=fechamento + timedelta(seconds=1))
        self.assertEqual(enviar_resumos_pendentes(), 1)
        self.assertEqual(enviar_resumos_pendentes(), 0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('33%', mail.outbox[0].body)
        self.assertIn('- Texto', mail.outbox[0].body)
        self.assertNotIn('- Vídeo', mail.outbox[0].body)
        self.assertEqual(ResumoSemanal.objects.count(), 1)

    def test_fechamento_dominical_18h_brasilia(self):
        fechamento = ultimo_fechamento()
        self.assertEqual(fechamento.weekday(), 6)
        self.assertEqual(fechamento.hour, 18)
        self.assertEqual(ultimo_fechamento(fechamento - timedelta(seconds=1)), fechamento - timedelta(days=7))
        self.assertEqual(ultimo_fechamento(fechamento), fechamento)

    def test_falha_de_email_preserva_envio_pendente(self):
        matricula, _ = self.comprar_curso()
        matricula.liberada_em = ultimo_fechamento() - timedelta(days=1)
        matricula.save()
        with patch('app.notificacoes.services.send_mail', side_effect=RuntimeError('indisponível')):
            with self.assertRaises(RuntimeError):
                enviar_resumos_pendentes()
        self.assertFalse(ResumoSemanal.objects.exists())
