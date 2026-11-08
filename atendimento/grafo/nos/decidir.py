"""Nó 7 · decidir (LLM): resolve automático vs. humano e propõe a ação, dentro da política.

TODO: implementar com gpt-oss-120b. Recebe classificação, contexto, elegibilidade e,
se houver, os problemas apontados pela auditoria anterior.
STUB conservador: sempre humano.
"""
from atendimento.dominio.schemas import Decisao
from atendimento.grafo.estado import EstadoAtendimento


def decidir(estado: EstadoAtendimento) -> dict:
    tentativa = estado.get("tentativas_decisao", 0) + 1
    d = Decisao(modo="humano", origem="llm", acao_proposta="revisao_manual",
                justificativa="[STUB] decisão automática ainda não implementada")
    return {"decisao": d, "tentativas_decisao": tentativa, "trilha": [f"decidir: [STUB] tentativa {tentativa} → humano"]}
