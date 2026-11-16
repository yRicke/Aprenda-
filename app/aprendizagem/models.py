import uuid

from django.db import models
from django.utils import timezone


class Matricula(models.Model):
    compra = models.OneToOneField('compras.Compra', on_delete=models.PROTECT, related_name='matricula')
    liberada_em = models.DateTimeField(default=timezone.now)
    concluida_em = models.DateTimeField('concluída em', null=True, blank=True)

    class Meta:
        verbose_name = 'matrícula'
        ordering = ('-liberada_em',)

    @property
    def total_aulas(self):
        return self.compra.curso.modulos.aggregate(total=models.Count('aulas'))['total']

    @property
    def pendencias(self):
        return self.total_aulas - self.conclusoes.count()

    @property
    def progresso(self):
        total = self.total_aulas
        return round(self.conclusoes.count() * 100 / total) if total else 0

    def __str__(self):
        return str(self.compra)


class ConclusaoAula(models.Model):
    matricula = models.ForeignKey(Matricula, on_delete=models.CASCADE, related_name='conclusoes')
    aula = models.ForeignKey('cursos.Aula', on_delete=models.PROTECT)
    concluida_em = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'conclusão de aula'
        verbose_name_plural = 'conclusões de aulas'
        constraints = [models.UniqueConstraint(fields=('matricula', 'aula'), name='conclusao_aula_unica')]


class TentativaQuestionario(models.Model):
    matricula = models.ForeignKey(Matricula, on_delete=models.CASCADE, related_name='tentativas')
    questionario = models.ForeignKey('cursos.Questionario', on_delete=models.PROTECT)
    respostas = models.JSONField()
    nota = models.DecimalField(max_digits=5, decimal_places=2)
    enviada_em = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'tentativa de questionário'
        verbose_name_plural = 'tentativas de questionário'
        ordering = ('-enviada_em',)


class Certificado(models.Model):
    matricula = models.OneToOneField(Matricula, on_delete=models.PROTECT, related_name='certificado')
    codigo = models.UUIDField('código', default=uuid.uuid4, unique=True, editable=False)
    emitido_em = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'certificado'

    def __str__(self):
        return str(self.codigo)
