from django.db import transaction

from .models import Curso


@transaction.atomic
def alternar_publicacao(curso_id):
    curso = Curso.objects.select_for_update().get(pk=curso_id)
    curso.publicado = not curso.publicado
    curso.save(update_fields=['publicado'])
    return curso
