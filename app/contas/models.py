from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    class Perfil(models.TextChoices):
        ALUNO = 'aluno', 'Aluno'
        INSTRUTOR = 'instrutor', 'Instrutor'

    email = models.EmailField('e-mail', unique=True)
    perfil = models.CharField('perfil', max_length=10, choices=Perfil, default=Perfil.ALUNO)

    @property
    def pode_instruir(self):
        return self.is_superuser or self.perfil == self.Perfil.INSTRUTOR

    @property
    def nome(self):
        return self.get_full_name() or self.username

    def __str__(self):
        return self.nome
