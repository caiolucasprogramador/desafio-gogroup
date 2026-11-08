"""Nó 6 · regras_fixas (determinístico): casos que NUNCA são decididos automaticamente.

Saúde → responsável técnica; Reclame Aqui → analista (resposta pública).
O desvio acontece aqui, e não logo após `classificar`, de propósito: até este ponto nada
chama LLM, e o humano recebe o dossiê completo (pedido, prioridade, checklist da política).
"""
from atendimento.grafo.estado import EstadoAtendimento
from atendimento.servicos.decisao import regra_fixa


def regras_fixas(estado: EstadoAtendimento) -> dict:
    d = regra_fixa(estado["classificacao"], estado.get("canal", ""))
    if d is None:
        return {"trilha": ["regras_fixas: nenhuma regra fixa → tabela de decisão"]}
    return {"decisao": d, "trilha": [f"regras_fixas: {d.justificativa}"]}
