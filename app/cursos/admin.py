from django.contrib import admin

from .models import AulaTexto, AulaVideo, Curso, Modulo, Questionario


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'instrutor', 'preco', 'publicado')
    list_filter = ('publicado',)
    search_fields = ('titulo',)
    actions = None

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and not (obj and obj.estrutura_bloqueada)


class EstruturaAdmin(admin.ModelAdmin):
    actions = None

    def curso(self, obj):
        return obj.curso if isinstance(obj, Modulo) else obj.modulo.curso

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and not (obj and self.curso(obj).estrutura_bloqueada)

    def has_delete_permission(self, request, obj=None):
        if not super().has_delete_permission(request, obj) or obj is None:
            return False
        curso = self.curso(obj)
        if curso.estrutura_bloqueada:
            return False
        if isinstance(obj, Modulo):
            return not curso.publicado or curso.modulos.count() > 1
        return not curso.publicado or obj.modulo.aulas.count() > 1


admin.site.register([Modulo, AulaVideo, AulaTexto, Questionario], EstruturaAdmin)
