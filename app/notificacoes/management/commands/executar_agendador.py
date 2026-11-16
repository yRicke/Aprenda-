import logging
import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from app.notificacoes.services import enviar_resumos_pendentes

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Mantém o envio semanal ativo. Verifica o fechamento a cada minuto.'

    def handle(self, *args, **options):
        self.stdout.write('Agendador ativo. Fechamento aos domingos às 18h em America/Sao_Paulo. Ctrl+C encerra.')
        try:
            while True:
                close_old_connections()
                try:
                    enviados = enviar_resumos_pendentes()
                    if enviados:
                        self.stdout.write(f'{enviados} resumo(s) enviado(s).')
                except Exception:
                    logger.exception('Falha no envio semanal. A próxima verificação repetirá o envio pendente.')
                time.sleep(60)
        except KeyboardInterrupt:
            self.stdout.write('Agendador encerrado.')
