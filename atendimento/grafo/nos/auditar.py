"""Nó 8 · auditar (regras + LLM): a decisão respeita a política e a elegibilidade?

TODO: checagens determinísticas (ex.: reembolso só se elegível) + LLM revisor independente.
STUB: aprova.
"""
from atendimento.dominio.schemas import Auditoria
from atendimento.grafo.estado import EstadoAtendimento


def auditar(estado: EstadoAtendimento) -> dict:
    return {"auditoria": Auditoria(aprovada=True), "trilha": ["auditar: [STUB] aprovada"]}
