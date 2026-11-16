from django.core.management.base import BaseCommand

from app.notificacoes.services import enviar_resumos_pendentes


class Command(BaseCommand):
    help = 'Envia os resumos pendentes do último domingo às 18h, horário de Brasília.'

    def handle(self, *args, **options):
        enviados = enviar_resumos_pendentes()
        self.stdout.write(self.style.SUCCESS(f'{enviados} resumo(s) enviado(s).'))
