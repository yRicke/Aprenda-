from django.contrib import admin

admin.site.site_header = 'Administração Aprenda+'
admin.site.site_title = 'Aprenda+'
admin.site.index_title = 'Gestão da plataforma'


class RegistroSomenteLeituraAdmin(admin.ModelAdmin):
    """Registros de negócio são produzidos pelos serviços da plataforma."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
