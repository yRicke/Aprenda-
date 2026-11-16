import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Cupom(models.Model):
    codigo = models.CharField('código', max_length=40, unique=True)
    percentual = models.DecimalField(max_digits=5, decimal_places=2, validators=[
        MinValueValidator(Decimal('0.01')), MaxValueValidator(100),
    ])
    valido_ate = models.DateTimeField('válido até')
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'cupom'
        verbose_name_plural = 'cupons'

    def validar(self, agora=None):
        return self.ativo and self.valido_ate >= (agora or timezone.now())

    def calcular_desconto(self, preco):
        return (preco * self.percentual / Decimal('100')).quantize(Decimal('0.01'))

    def clean(self):
        super().clean()
        self.codigo = self.codigo.strip().upper()

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.codigo


class SolicitacaoPagamento(models.Model):
    class Estado(models.TextChoices):
        PENDENTE = 'pendente', 'Aguardando confirmação'
        AUTORIZADO = 'autorizado', 'Autorizado'
        RECUSADO = 'recusado', 'Recusado'

    chave = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    aluno = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    curso = models.ForeignKey('cursos.Curso', on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    cupom = models.ForeignKey(Cupom, on_delete=models.PROTECT, null=True, blank=True)
    estado = models.CharField(max_length=12, choices=Estado, default=Estado.PENDENTE)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'solicitação de pagamento'
        verbose_name_plural = 'solicitações de pagamento'
        constraints = [models.UniqueConstraint(
            fields=('aluno', 'curso'), condition=models.Q(estado='pendente'), name='pagamento_pendente_unico'
        )]


class Compra(models.Model):
    aluno = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='compras')
    curso = models.ForeignKey('cursos.Curso', on_delete=models.PROTECT, related_name='compras')
    cupom = models.ForeignKey(Cupom, on_delete=models.PROTECT, null=True, blank=True)
    valor_final = models.DecimalField(max_digits=10, decimal_places=2)
    confirmada_em = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'compra'
        constraints = [models.UniqueConstraint(fields=('aluno', 'curso'), name='compra_aluno_curso_unica')]

    def __str__(self):
        return f'{self.aluno} — {self.curso}'


class Pagamento(models.Model):
    compra = models.OneToOneField(Compra, on_delete=models.CASCADE, related_name='pagamento')
    solicitacao = models.OneToOneField(SolicitacaoPagamento, on_delete=models.PROTECT)
    referencia = models.CharField('referência', max_length=100, unique=True)
    autorizado_em = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'pagamento'
