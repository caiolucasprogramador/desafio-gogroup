"""Nó 3 · enriquecer (determinístico): cruza com pedido, histórico do cliente e estado da conversa.

Também corrige a classificação quando um FATO contradiz o texto
(ex.: rastreio_status → atraso se status_entrega = atrasado).
"""
from atendimento.dominio.parametros import DATA_REFERENCIA
from atendimento.grafo.estado import EstadoAtendimento
from atendimento.servicos.enriquecimento import enriquecer as enriquecer_conversa


def enriquecer(estado: EstadoAtendimento) -> dict:
    ctx, classificacao = enriquecer_conversa(
        estado["conversation_id"], estado.get("customer_id"), estado.get("order_id"),
        estado["data_abertura"], estado["classificacao"], estado.get("agora", DATA_REFERENCIA),
    )
    resumo = (f"pedido {ctx.order_id} R${ctx.valor} {ctx.status_entrega}; "
              f"{ctx.contatos_anteriores_pedido} contato(s) anterior(es) sobre o pedido; "
              f"{'aguardando resposta há ' + format(ctx.horas_aguardando, '.0f') + 'h' if ctx.aguardando_resposta else 'sem resposta pendente'}")
    if ctx.correcoes:
        resumo += " | correções: " + "; ".join(ctx.correcoes)
    return {"contexto": ctx, "classificacao": classificacao, "trilha": [f"enriquecer: {resumo}"]}
