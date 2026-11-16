from dataclasses import dataclass


@dataclass(frozen=True)
class ResultadoPagamento:
    estado: str
    referencia: str = ''


class OperadoraSimulada:
    """Contrato substituível por uma operadora que suporte chave de idempotência."""

    def autorizar(self, *, valor, token, chave):
        if token == 'recusar':
            return ResultadoPagamento('recusado')
        if token == 'sem_resposta':
            return ResultadoPagamento('pendente')
        if token != 'aprovar':
            raise ValueError('Token de simulação inválido.')
        return ResultadoPagamento('autorizado', f'SIM-{chave}')

    def consultar(self, *, chave):
        # A simulação de timeout termina como recusada na consulta, sem nova cobrança.
        return ResultadoPagamento('recusado')
