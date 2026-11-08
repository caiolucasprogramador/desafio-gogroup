"""Nó 3 · enriquecer (determinístico): cruza com pedidos e histórico do cliente.

TODO: implementar — join com pedidos.csv, dias desde o pedido, nº de pedidos/contatos do
cliente e correções factuais (rastreio_status → atraso quando status_entrega = atrasado).
"""
from atendimento.dominio.schemas import ContextoPedido
from atendimento.grafo.estado import EstadoAtendimento


def enriquecer(estado: EstadoAtendimento) -> dict:
    ctx = ContextoPedido(order_id=estado.get("order_id"), valor=None, status_entrega=None, transportadora=None,
                         dias_desde_pedido=None, n_pedidos_cliente=0, n_contatos_cliente=0)
    return {"contexto": ctx, "trilha": ["enriquecer: [STUB] sem dados do pedido ainda"]}
