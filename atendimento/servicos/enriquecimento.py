"""Enriquecimento: fatos do pedido, do cliente e da conversa + correções factuais da classificação."""
import pandas as pd

from atendimento.dominio.parametros import DATA_REFERENCIA
from atendimento.dominio.schemas import Classificacao, ContextoPedido, MotivoIdentificado
from atendimento.dominio.taxonomia import MOTIVO_PARA_CATEGORIA
from atendimento.servicos import dados
from atendimento.servicos.classificacao import motivo_principal


def corrigir_por_fatos(c: Classificacao, status_entrega: str | None) -> tuple[Classificacao, list[str]]:
    """O dado do pedido vence a interpretação do texto quando os dois divergem."""
    motivos = [m.motivo for m in c.motivos]
    if status_entrega == "atrasado" and "rastreio_status" in motivos and "atraso" not in motivos:
        novos = [MotivoIdentificado(motivo="atraso", evidencia="status_entrega=atrasado (pedidos.csv)")
                 if m.motivo == "rastreio_status" else m for m in c.motivos]
        principal = motivo_principal([m.motivo for m in novos])
        corrigida = c.model_copy(update={"motivos": novos, "motivo_principal": principal,
                                         "categoria_principal": MOTIVO_PARA_CATEGORIA[principal]})
        return corrigida, ["rastreio_status → atraso (pedido consta como atrasado)"]
    return c, []


def enriquecer(conversation_id: str, customer_id: str | None, order_id: str | None,
               data_abertura: str, classificacao: Classificacao,
               agora: str = DATA_REFERENCIA) -> tuple[ContextoPedido, Classificacao]:
    abertura, agora_ts = pd.Timestamp(data_abertura), pd.Timestamp(agora)

    ped = dados.pedidos()
    p = ped.loc[order_id] if order_id in ped.index else None

    conv = dados.conversas()
    anteriores = conv[conv.data_abertura < abertura]
    msgs = dados.mensagens()
    msgs = msgs[(msgs.conversation_id == conversation_id) & (msgs.timestamp <= agora_ts)]
    ultima = msgs.iloc[-1] if len(msgs) else None
    aguardando = ultima is not None and ultima.autor == "cliente"

    classificacao, correcoes = corrigir_por_fatos(classificacao, p.status_entrega if p is not None else None)
    ctx = ContextoPedido(
        order_id=order_id,
        valor=float(p.valor) if p is not None else None,
        status_entrega=p.status_entrega if p is not None else None,
        transportadora=p.transportadora if p is not None else None,
        dias_desde_pedido=(abertura.normalize() - p.data_pedido).days if p is not None else None,
        n_pedidos_cliente=int((ped.customer_id == customer_id).sum()),
        contatos_anteriores_cliente=int((anteriores.customer_id == customer_id).sum()),
        contatos_anteriores_pedido=int((anteriores.order_id == order_id).sum()) if order_id else 0,
        aguardando_resposta=aguardando,
        horas_aguardando=max(0.0, (agora_ts - ultima.timestamp).total_seconds() / 3600) if aguardando else None,
        correcoes=correcoes,
    )
    return ctx, classificacao


def contexto_simulado(pedido: dict, classificacao: Classificacao) -> tuple[ContextoPedido, Classificacao]:
    """Modo demonstração: o contexto vem de um pedido fictício informado pelo chamador.

    Não lê nenhum CSV do case: é o que permite publicar o agente sem expor os dados.
    Chaves aceitas: valor, status_entrega (None = sem pedido), dias_desde_pedido,
    transportadora, contatos_anteriores_pedido.
    """
    status = pedido.get("status_entrega")
    tem_pedido = status is not None
    classificacao, correcoes = corrigir_por_fatos(classificacao, status)
    anteriores = int(pedido.get("contatos_anteriores_pedido") or 0)
    ctx = ContextoPedido(
        order_id="PEDIDO-DEMO" if tem_pedido else None,
        valor=float(pedido["valor"]) if tem_pedido and pedido.get("valor") is not None else None,
        status_entrega=status,
        transportadora=pedido.get("transportadora") if tem_pedido else None,
        dias_desde_pedido=int(pedido["dias_desde_pedido"]) if tem_pedido and pedido.get("dias_desde_pedido") is not None else None,
        n_pedidos_cliente=1 if tem_pedido else 0,
        contatos_anteriores_cliente=anteriores,
        contatos_anteriores_pedido=anteriores if tem_pedido else 0,
        aguardando_resposta=True,  # o cliente acabou de escrever
        horas_aguardando=0.0,
        correcoes=correcoes,
    )
    return ctx, classificacao
