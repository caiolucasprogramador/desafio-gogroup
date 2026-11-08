"""Nó 4 · priorizar (determinístico): score 0–100 = média ponderada de fatores (dominio/parametros.py)."""
from atendimento.grafo.estado import EstadoAtendimento
from atendimento.servicos.priorizacao import explicar, priorizar as calcular


def priorizar(estado: EstadoAtendimento) -> dict:
    p = calcular(estado["classificacao"], estado["contexto"], estado["canal"], estado.get("status_conversa"))
    return {"prioridade": p, "trilha": [f"priorizar: {explicar(p)}"]}
