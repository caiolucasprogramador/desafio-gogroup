"""Nó 4 · priorizar (determinístico): score 0–100 com componentes explícitos.

TODO: implementar pesos finais (gravidade, canal, SLA, recontato, valor, tom).
Por enquanto o score é só a gravidade do motivo principal.
"""
from atendimento.dominio.schemas import Prioridade
from atendimento.dominio.taxonomia import GRAVIDADE, SEMPRE_HUMANO
from atendimento.grafo.estado import EstadoAtendimento


def priorizar(estado: EstadoAtendimento) -> dict:
    principal = estado["classificacao"].motivo_principal
    p = Prioridade(score=GRAVIDADE[principal], componentes={"gravidade": GRAVIDADE[principal]},
                   topo_da_fila=principal in SEMPRE_HUMANO)
    return {"prioridade": p, "trilha": [f"priorizar: [STUB] score={p.score:.0f} (só gravidade)"]}
