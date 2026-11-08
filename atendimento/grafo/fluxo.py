"""Montagem do grafo: o fluxo que toda conversa percorre.

    START → anonimizar → classificar ─┬─(sem_conteudo)→ END
                                      └→ enriquecer → priorizar → checar_elegibilidade → regras_fixas
    regras_fixas ─┬─(saúde / Reclame Aqui)→ escalar_humano → END
                  └→ decidir ─┬─(todos os motivos automáticos)→ agir → END
                              └─(algum motivo exige humano)→ escalar_humano → END

O antigo nó `auditar` foi removido: com o `decidir` determinístico, repetir a decisão
daria o mesmo resultado. As garantias que ele checaria (saúde nunca automática, ação com
custo só se elegível e dentro do limite, nenhum motivo esquecido) viraram testes em
tests/test_invariantes.py, rodados contra a fila inteira.
"""
from langgraph.graph import END, START, StateGraph

from atendimento.grafo import nos
from atendimento.grafo.estado import EstadoAtendimento
from atendimento.grafo.roteamento import apos_classificar, apos_decidir, apos_regras_fixas


def construir_grafo():
    g = StateGraph(EstadoAtendimento)

    g.add_node("anonimizar", nos.anonimizar)
    g.add_node("classificar", nos.classificar)
    g.add_node("enriquecer", nos.enriquecer)
    g.add_node("priorizar", nos.priorizar)
    g.add_node("checar_elegibilidade", nos.checar_elegibilidade)
    g.add_node("regras_fixas", nos.regras_fixas)
    g.add_node("decidir", nos.decidir)
    g.add_node("agir", nos.agir)
    g.add_node("escalar_humano", nos.escalar_humano)

    g.add_edge(START, "anonimizar")
    g.add_edge("anonimizar", "classificar")
    g.add_conditional_edges("classificar", apos_classificar)
    g.add_edge("enriquecer", "priorizar")
    g.add_edge("priorizar", "checar_elegibilidade")
    g.add_edge("checar_elegibilidade", "regras_fixas")
    g.add_conditional_edges("regras_fixas", apos_regras_fixas)
    g.add_conditional_edges("decidir", apos_decidir)
    g.add_edge("agir", END)
    g.add_edge("escalar_humano", END)

    return g.compile()


grafo = construir_grafo()
