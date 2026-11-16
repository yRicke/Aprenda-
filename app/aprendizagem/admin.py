from django.contrib import admin

from app.admin import RegistroSomenteLeituraAdmin

from .models import Certificado, ConclusaoAula, Matricula, TentativaQuestionario


@admin.register(Matricula)
class MatriculaAdmin(RegistroSomenteLeituraAdmin):
    list_display = ('id', 'compra', 'liberada_em', 'concluida_em')


admin.site.register([Certificado, ConclusaoAula, TentativaQuestionario], RegistroSomenteLeituraAdmin)
