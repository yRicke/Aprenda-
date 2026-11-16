from django.contrib import admin

from app.admin import RegistroSomenteLeituraAdmin

from .models import Compra, Cupom, Pagamento, SolicitacaoPagamento


@admin.register(Cupom)
class CupomAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'percentual', 'valido_ate', 'ativo')
    search_fields = ('codigo',)


@admin.register(Compra)
class CompraAdmin(RegistroSomenteLeituraAdmin):
    list_display = ('id', 'aluno', 'curso', 'valor_final', 'confirmada_em')


@admin.register(SolicitacaoPagamento)
class SolicitacaoAdmin(RegistroSomenteLeituraAdmin):
    list_display = ('chave', 'aluno', 'curso', 'estado', 'valor')


admin.site.register(Pagamento, RegistroSomenteLeituraAdmin)
