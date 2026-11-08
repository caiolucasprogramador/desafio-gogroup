"""Nó terminal · escalar_humano: envia à fila humana certa com o DOSSIÊ do caso.

O humano não começa do zero: recebe motivo, fatos do pedido, prioridade e explicação,
o que a política exige/permite, o que falta pedir e as ações sugeridas por motivo.
"""
from atendimento.dominio.schemas import Acao
from atendimento.grafo.estado import EstadoAtendimento
from atendimento.servicos.priorizacao import explicar


def escalar_humano(estado: EstadoAtendimento) -> dict:
    d, p, c = estado["decisao"], estado["prioridade"], estado["classificacao"]
    ctx, e = estado.get("contexto"), estado.get("elegibilidade")
    dossie = {
        "fila": d.fila_destino,
        "prioridade": {"score": p.score, "topo_da_fila": p.topo_da_fila, "explicacao": explicar(p)},
        "motivo_escalonamento": d.justificativa,
        "motivos": [{"motivo": m.motivo, "evidencia": m.evidencia} for m in c.motivos],
        "pedido": ctx.model_dump(include={"order_id", "valor", "status_entrega", "transportadora",
                                          "dias_desde_pedido"}) if ctx else None,
        "politicas": [a.model_dump(include={"motivo", "resultado", "justificativa", "informacoes_faltantes",
                                            "observacoes"}) for a in e.avaliacoes] if e else [],
        "acoes_sugeridas": [a.model_dump() for a in d.acoes],
    }
    acao = Acao(tipo=d.acao_proposta, destino="fila_humana", payload=dossie)
    return {"acao": acao, "trilha": [f"escalar_humano: fila '{d.fila_destino}' "
                                     f"(score {p.score:g}{', TOPO' if p.topo_da_fila else ''})"]}
