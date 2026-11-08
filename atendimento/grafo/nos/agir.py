"""Nó 8 · agir: registra as ações automáticas (simuladas) e redige a resposta ao cliente.

Rascunho padrão: templates determinísticos (servicos/respostas.py), um parágrafo por motivo.
Com REDACAO_LLM=1, o LLM reescreve o rascunho em tom mais natural (servicos/redacao.py);
se o texto do LLM falhar nas checagens de segurança, o template é mantido.
"""
import os

from atendimento.dominio.schemas import Acao
from atendimento.grafo.estado import EstadoAtendimento
from atendimento.servicos.respostas import redigir


def agir(estado: EstadoAtendimento) -> dict:
    d = estado["decisao"]
    rascunho, origem = redigir(d, estado.get("marca", "")), "template"
    if os.environ.get("REDACAO_LLM") == "1" and os.environ.get("SEM_LLM") != "1":
        from atendimento.servicos.redacao import reescrever
        rascunho, origem = reescrever(rascunho, d, estado.get("mensagens_cliente", []), estado.get("marca", ""))
    acao = Acao(tipo=d.acao_proposta, destino="automatico", rascunho_resposta=rascunho,
                payload={"acoes": [a.model_dump() for a in d.acoes], "origem_rascunho": origem})
    tipos = ", ".join(a.tipo for a in d.acoes)
    return {"acao": acao, "trilha": [f"agir: ações registradas ({tipos}); rascunho via {origem}"]}
