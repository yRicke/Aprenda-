from django.db import models
from django.utils import timezone


class AvisoConclusao(models.Model):
    matricula = models.OneToOneField('aprendizagem.Matricula', on_delete=models.PROTECT, related_name='aviso')
    publicado_em = models.DateTimeField(default=timezone.now)
    lido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'aviso de conclusão'
        verbose_name_plural = 'avisos de conclusão'
        ordering = ('-publicado_em',)


class ResumoSemanal(models.Model):
    matricula = models.ForeignKey('aprendizagem.Matricula', on_delete=models.PROTECT, related_name='resumos')
    fechamento = models.DateTimeField()
    enviado_em = models.DateTimeField(default=timezone.now)
    conteudo = models.TextField('conteúdo')

    class Meta:
        verbose_name = 'resumo semanal'
        verbose_name_plural = 'resumos semanais'
        constraints = [models.UniqueConstraint(fields=('matricula', 'fechamento'), name='resumo_semanal_unico')]
