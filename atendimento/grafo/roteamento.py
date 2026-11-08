"""Arestas condicionais: funções puras que olham o estado e escolhem o próximo nó."""
from typing import Literal

from langgraph.graph import END

from atendimento.grafo.estado import EstadoAtendimento


def apos_classificar(estado: EstadoAtendimento) -> Literal["enriquecer", "__end__"]:
    """Abandono no bot (cliente não escreveu nada): não há o que resolver."""
    return END if estado["classificacao"].motivo_principal == "sem_conteudo" else "enriquecer"


def apos_regras_fixas(estado: EstadoAtendimento) -> Literal["escalar_humano", "decidir"]:
    """Se uma regra fixa já decidiu (saúde, Reclame Aqui), vai direto para humano."""
    return "escalar_humano" if estado.get("decisao") else "decidir"


def apos_decidir(estado: EstadoAtendimento) -> Literal["agir", "escalar_humano"]:
    """Conversa automática só se TODOS os motivos tiverem ação automática (garantido pelo decidir)."""
    return "agir" if estado["decisao"].modo == "automatico" else "escalar_humano"
