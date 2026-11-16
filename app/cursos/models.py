from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class Curso(models.Model):
    instrutor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='cursos')
    titulo = models.CharField('título', max_length=180)
    descricao = models.TextField('descrição')
    preco = models.DecimalField('preço', max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    publicado = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-criado_em',)
        verbose_name = 'curso'

    @property
    def estrutura_bloqueada(self):
        return bool(self.pk and self.compras.exists())

    def clean(self):
        super().clean()
        if self.instrutor_id and not self.instrutor.pode_instruir:
            raise ValidationError({'instrutor': 'Selecione um instrutor.'})
        if self.pk and self.estrutura_bloqueada:
            anterior = Curso.objects.get(pk=self.pk)
            if anterior.instrutor_id != self.instrutor_id:
                raise ValidationError('O instrutor fica fixo após a primeira compra.')
        if self.publicado:
            if not self.pk or not self.modulos.exists():
                raise ValidationError('Adicione pelo menos um módulo antes de publicar.')
            if self.modulos.filter(aulas__isnull=True).exists():
                raise ValidationError('Cada módulo precisa de pelo menos uma aula para publicar.')

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.estrutura_bloqueada:
            raise ValidationError('Um curso com compra confirmada não pode ser excluído.')
        return super().delete(*args, **kwargs)

    def __str__(self):
        return self.titulo


class Modulo(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='modulos')
    titulo = models.CharField('título', max_length=180)
    ordem = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        ordering = ('ordem', 'pk')
        verbose_name = 'módulo'
        constraints = [models.UniqueConstraint(fields=('curso', 'ordem'), name='modulo_ordem_unica')]

    def clean(self):
        super().clean()
        if self.curso_id:
            validar_estrutura(self.curso)
            if not self.pk and self.curso.publicado:
                raise ValidationError('Despublique o curso antes de adicionar um módulo vazio.')
        if self.pk:
            anterior = Modulo.objects.select_related('curso').get(pk=self.pk)
            if anterior.curso_id != self.curso_id:
                raise ValidationError('O módulo deve permanecer no curso de origem.')

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        validar_estrutura(self.curso)
        if self.curso.publicado and self.curso.modulos.count() == 1:
            raise ValidationError('Despublique o curso antes de excluir seu último módulo.')
        return super().delete(*args, **kwargs)

    def __str__(self):
        return self.titulo


def validar_estrutura(curso):
    if curso.estrutura_bloqueada:
        raise ValidationError('A estrutura do curso fica fixa após a primeira compra confirmada.')


class Aula(models.Model):
    class Tipo(models.TextChoices):
        VIDEO = 'video', 'Vídeo'
        TEXTO = 'texto', 'Texto'
        QUESTIONARIO = 'questionario', 'Questionário'

    modulo = models.ForeignKey(Modulo, on_delete=models.CASCADE, related_name='aulas')
    titulo = models.CharField('título', max_length=180)
    ordem = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    tipo = models.CharField(max_length=15, choices=Tipo, editable=False)

    class Meta:
        ordering = ('modulo__ordem', 'ordem', 'pk')
        verbose_name = 'aula'
        constraints = [models.UniqueConstraint(fields=('modulo', 'ordem'), name='aula_ordem_unica')]

    @property
    def conteudo(self):
        return getattr(self, {'video': 'aulavideo', 'texto': 'aulatexto', 'questionario': 'questionario'}[self.tipo])

    def clean(self):
        super().clean()
        if self.modulo_id:
            validar_estrutura(self.modulo.curso)
        if self.pk:
            anterior = Aula.objects.get(pk=self.pk)
            if anterior.modulo_id != self.modulo_id or anterior.tipo != self.tipo:
                raise ValidationError('A aula deve manter seu módulo e tipo de origem.')

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        validar_estrutura(self.modulo.curso)
        if self.modulo.curso.publicado and self.modulo.aulas.count() == 1:
            raise ValidationError('Despublique o curso antes de excluir a última aula de um módulo.')
        return super().delete(*args, **kwargs)

    def __str__(self):
        return self.titulo


class AulaVideo(Aula):
    url_video = models.URLField('URL do vídeo')
    duracao_segundos = models.PositiveIntegerField('duração em segundos', default=0)

    class Meta:
        verbose_name = 'aula em vídeo'

    @property
    def url_incorporacao(self):
        url = urlparse(self.url_video)
        identificador = ''
        if url.hostname in ('www.youtube.com', 'youtube.com'):
            identificador = parse_qs(url.query).get('v', [''])[0]
        elif url.hostname == 'youtu.be':
            identificador = url.path.strip('/')
        if identificador and all(caractere.isalnum() or caractere in '-_' for caractere in identificador):
            return f'https://www.youtube-nocookie.com/embed/{identificador}'
        return None

    def save(self, *args, **kwargs):
        self.tipo = Aula.Tipo.VIDEO
        return super().save(*args, **kwargs)


class AulaTexto(Aula):
    texto = models.TextField('conteúdo')

    class Meta:
        verbose_name = 'aula em texto'

    def save(self, *args, **kwargs):
        self.tipo = Aula.Tipo.TEXTO
        return super().save(*args, **kwargs)


def validar_questoes(questoes):
    if not isinstance(questoes, list) or not questoes:
        raise ValidationError('Informe pelo menos uma questão.')
    for questao in questoes:
        if not isinstance(questao, dict):
            raise ValidationError('Cada questão deve ser um objeto JSON.')
        opcoes = questao.get('opcoes')
        correta = questao.get('correta')
        if not isinstance(questao.get('enunciado'), str) or not questao['enunciado'].strip():
            raise ValidationError('Cada questão precisa de um enunciado.')
        if not isinstance(opcoes, list) or len(opcoes) < 2 or any(
            not isinstance(opcao, str) or not opcao.strip() for opcao in opcoes
        ):
            raise ValidationError('Cada questão precisa de pelo menos duas opções de texto.')
        if type(correta) is not int or not 0 <= correta < len(opcoes):
            raise ValidationError('A resposta correta é o índice da opção, começando em zero.')


class Questionario(Aula):
    questoes = models.JSONField('questões', validators=[validar_questoes])

    class Meta:
        verbose_name = 'questionário'

    def save(self, *args, **kwargs):
        self.tipo = Aula.Tipo.QUESTIONARIO
        return super().save(*args, **kwargs)
