"""Nó 9 · agir: registra a ação automática (simulada) e redige a resposta ao cliente.

TODO: tipos de ação estruturados (estorno, reenvio, cancelamento, informar rastreio...) + rascunho via LLM.
"""
from atendimento.dominio.schemas import Acao
from atendimento.grafo.estado import EstadoAtendimento


def agir(estado: EstadoAtendimento) -> dict:
    d = estado["decisao"]
    acao = Acao(tipo=d.acao_proposta, destino="automatico")
    return {"acao": acao, "trilha": [f"agir: [STUB] ação '{acao.tipo}' registrada"]}
