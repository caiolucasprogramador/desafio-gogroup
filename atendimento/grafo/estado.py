"""Estado do grafo: o "prontuário" de uma conversa, preenchido nó a nó.

Cada nó lê o que precisa e devolve APENAS as chaves que produz;
o LangGraph faz o merge no estado. `trilha` acumula (operator.add) para auditoria.
"""
import operator
from typing import Annotated, TypedDict

from atendimento.dominio.schemas import (
    Acao, Auditoria, Classificacao, ContextoPedido, Decisao, Elegibilidade, Prioridade,
)


class EstadoAtendimento(TypedDict, total=False):
    # Entrada ------------------------------------------------------------ (quem preenche)
    conversation_id: str                 # chamador
    customer_id: str                     # chamador
    order_id: str | None                 # chamador
    canal: str                           # chamador: whatsapp | email | reclame_aqui
    marca: str                           # chamador
    data_abertura: str                   # chamador
    status_conversa: str                 # chamador: pendente | reaberto | ...
    mensagens_cliente: list[str]         # chamador → anonimizar (substitui por versão mascarada)

    # Produzido pelos nós ------------------------------------------------
    classificacao: Classificacao         # classificar
    contexto: ContextoPedido             # enriquecer
    prioridade: Prioridade               # priorizar
    elegibilidade: Elegibilidade         # checar_elegibilidade
    decisao: Decisao                     # regras_fixas | decidir
    auditoria: Auditoria                 # auditar
    tentativas_decisao: int              # decidir (limita o loop decidir ↔ auditar)
    acao: Acao                           # agir | escalar_humano

    # Trilha de auditoria: cada nó anexa uma linha explicando o que fez
    trilha: Annotated[list[str], operator.add]
