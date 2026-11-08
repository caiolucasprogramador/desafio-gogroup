"""Score de prioridade: média ponderada de fatores 0–100 (pesos em dominio/parametros.py)."""
from atendimento.dominio.parametros import (
    CUSTO_CONVERSA, FATOR_MOTIVOS_SECUNDARIOS, PESOS_PRIORIDADE, SLA_HORAS, VALOR_TETO_PRIORIDADE,
)
from atendimento.dominio.schemas import Classificacao, ContextoPedido, Prioridade
from atendimento.dominio.taxonomia import GRAVIDADE, SEMPRE_HUMANO


def gravidade_conversa(motivos: list[str]) -> float:
    """Motivo mais grave + fração da soma dos demais, com teto 100."""
    if not motivos:
        return 0.0
    notas = sorted((GRAVIDADE[m] for m in set(motivos)), reverse=True)
    return min(100.0, notas[0] + FATOR_MOTIVOS_SECUNDARIOS * sum(notas[1:]))


def fatores(c: Classificacao, ctx: ContextoPedido, canal: str, status_conversa: str | None) -> dict[str, float]:
    sla = 0.0
    if ctx.aguardando_resposta and ctx.horas_aguardando is not None:
        sla = min(100.0, 100 * ctx.horas_aguardando / SLA_HORAS.get(canal, 24.0))
    voltou = c.recontato or status_conversa == "reaberto" or ctx.contatos_anteriores_pedido > 0
    return {
        "gravidade": gravidade_conversa([m.motivo for m in c.motivos]),
        "canal": 100 * CUSTO_CONVERSA.get(canal, 0) / max(CUSTO_CONVERSA.values()),
        "sla": sla,
        "recontato": 100.0 if voltou else 0.0,
        "valor": min(100.0, 100 * (ctx.valor or 0) / VALOR_TETO_PRIORIDADE),
        "tom": 100.0 if c.tom in ("irritado", "urgente") else 0.0,
    }


def priorizar(c: Classificacao, ctx: ContextoPedido, canal: str, status_conversa: str | None = None) -> Prioridade:
    f = fatores(c, ctx, canal, status_conversa)
    contrib = {k: round(v * PESOS_PRIORIDADE[k], 1) for k, v in f.items()}
    return Prioridade(
        score=round(sum(contrib.values()), 1),
        fatores={k: round(v, 1) for k, v in f.items()},
        contribuicoes=contrib,
        topo_da_fila=bool({m.motivo for m in c.motivos} & SEMPRE_HUMANO),
    )


def explicar(p: Prioridade) -> str:
    """Ex.: 'score 71.5 = gravidade 32.0 + canal 15.0 + sla 15.0 + ...' (só fatores que somaram)."""
    partes = " + ".join(f"{k} {v:g}" for k, v in sorted(p.contribuicoes.items(), key=lambda kv: -kv[1]) if v)
    return f"score {p.score:g} = {partes or '0'}" + (" | TOPO (saúde)" if p.topo_da_fila else "")
