"""Nó terminal · escalar_humano: coloca na fila humana com prioridade e motivo do escalonamento."""
from atendimento.dominio.schemas import Acao
from atendimento.grafo.estado import EstadoAtendimento


def escalar_humano(estado: EstadoAtendimento) -> dict:
    d, p = estado["decisao"], estado["prioridade"]
    acao = Acao(tipo=d.acao_proposta, destino="fila_humana",
                payload={"score": p.score, "topo_da_fila": p.topo_da_fila, "motivo_escalonamento": d.justificativa})
    return {"acao": acao, "trilha": [f"escalar_humano: fila humana (score {p.score:.0f}{', TOPO' if p.topo_da_fila else ''})"]}
