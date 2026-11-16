from django.contrib import admin

from app.admin import RegistroSomenteLeituraAdmin

from .models import AvisoConclusao, ResumoSemanal

admin.site.register([AvisoConclusao, ResumoSemanal], RegistroSomenteLeituraAdmin)
