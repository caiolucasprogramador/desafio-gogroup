"""Fábricas de objetos para testes: sem CSV, sem LLM."""
import pytest

from atendimento.dominio.schemas import Classificacao, ContextoPedido, MotivoIdentificado
from atendimento.dominio.taxonomia import MOTIVO_PARA_CATEGORIA
from atendimento.servicos.classificacao import motivo_principal


def classif(*motivos: str, tom: str = "neutro", recontato: bool = False) -> Classificacao:
    principal = motivo_principal(list(motivos))
    return Classificacao(
        motivos=[MotivoIdentificado(motivo=m, evidencia="...") for m in motivos], recontato=recontato, tom=tom,
        confianca="alta", motivo_principal=principal, categoria_principal=MOTIVO_PARA_CATEGORIA[principal],
        origem="llm",
    )


def contexto(status="entregue", dias=5, valor=80.0, order_id="GB1", **extra) -> ContextoPedido:
    base = dict(order_id=order_id, valor=valor, status_entrega=status, transportadora="Rota Express",
                dias_desde_pedido=dias, n_pedidos_cliente=1, contatos_anteriores_cliente=0,
                contatos_anteriores_pedido=0, aguardando_resposta=False, horas_aguardando=None)
    return ContextoPedido(**(base | extra))


@pytest.fixture
def fab():
    return type("Fab", (), {"classif": staticmethod(classif), "contexto": staticmethod(contexto)})
