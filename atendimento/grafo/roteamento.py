"""Arestas condicionais: funções puras que olham o estado e escolhem o próximo nó."""
from typing import Literal

from langgraph.graph import END

from atendimento.grafo.estado import EstadoAtendimento

MAX_TENTATIVAS_DECISAO = 2  # decidir → auditar reprova → decidir de novo (1x) → escala


def apos_classificar(estado: EstadoAtendimento) -> Literal["enriquecer", "__end__"]:
    """Abandono no bot (cliente não escreveu nada): não há o que resolver."""
    return END if estado["classificacao"].motivo_principal == "sem_conteudo" else "enriquecer"


def apos_regras_fixas(estado: EstadoAtendimento) -> Literal["escalar_humano", "decidir"]:
    """Se uma regra fixa já decidiu, o LLM não participa."""
    return "escalar_humano" if estado.get("decisao") else "decidir"


def apos_auditar(estado: EstadoAtendimento) -> Literal["agir", "escalar_humano", "decidir"]:
    if estado["auditoria"].aprovada:
        return "agir" if estado["decisao"].modo == "automatico" else "escalar_humano"
    if estado.get("tentativas_decisao", 0) < MAX_TENTATIVAS_DECISAO:
        return "decidir"  # volta com os problemas apontados
    return "escalar_humano"
