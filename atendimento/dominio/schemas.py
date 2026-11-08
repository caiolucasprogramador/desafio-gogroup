"""Contratos de dados do grafo."""
from typing import Literal

from pydantic import BaseModel, Field

from atendimento.dominio.taxonomia import MOTIVOS, TONS

Motivo = Literal[tuple(MOTIVOS)]  # type: ignore[valid-type]
Tom = Literal[TONS]  # type: ignore[valid-type]


class MotivoIdentificado(BaseModel):
    motivo: Motivo = Field(description="Motivo da taxonomia.")
    evidencia: str = Field(description="Trecho literal da mensagem do cliente que comprova o motivo.")


class ClassificacaoLLM(BaseModel):
    """Saída estruturada pedida ao LLM."""

    motivos: list[MotivoIdentificado] = Field(
        description="Todos os motivos do contato, na ordem em que o cliente os menciona."
    )
    recontato: bool = Field(
        description="True se o cliente indica que já procurou antes (ex.: 'de novo aqui', "
        "'já é a 2ª vez', 'ninguém me respondeu')."
    )
    tom: Tom = Field(
        description="irritado (reclamação agressiva, sarcasmo, indignação), urgente (precisa de "
        "solução imediata, sintoma persistente, prazo pessoal) ou neutro."
    )
    confianca: Literal["alta", "media", "baixa"] = Field(
        description="Confiança na classificação; baixa se a mensagem for ambígua."
    )


class Classificacao(ClassificacaoLLM):
    """Classificação final: saída do LLM + campos derivados por regra."""

    motivo_principal: Motivo
    categoria_principal: str
    origem: Literal["llm", "regra"]
    modelo: str | None = None


# --- Etapas seguintes do grafo -------------------------------------------------

class ContextoPedido(BaseModel):
    """Saída de `enriquecer`: fatos do pedido e do cliente (sem LLM)."""

    order_id: str | None
    valor: float | None
    status_entrega: str | None
    transportadora: str | None
    dias_desde_pedido: int | None
    n_pedidos_cliente: int
    n_contatos_cliente: int
    motivos_corrigidos: list[str] = Field(
        default_factory=list,
        description="Ajustes feitos com base em fatos (ex.: rastreio_status → atraso se status_entrega=atrasado).",
    )


class Prioridade(BaseModel):
    """Saída de `priorizar`: score determinístico e seus componentes (auditável)."""

    score: float = Field(ge=0, le=100)
    componentes: dict[str, float]
    topo_da_fila: bool = Field(description="True para saúde: fura a fila independentemente do score.")


class Elegibilidade(BaseModel):
    """Saída de `checar_elegibilidade`: o caso cabe na política?"""

    resultado: Literal["elegivel", "inelegivel", "indeterminado", "sem_politica"]
    politica: str | None
    justificativa: str
    informacoes_faltantes: list[str] = Field(default_factory=list)


class Decisao(BaseModel):
    """Saída de `regras_fixas` ou `decidir`."""

    modo: Literal["automatico", "humano"]
    acao_proposta: str
    justificativa: str
    origem: Literal["regra", "llm"]


class Auditoria(BaseModel):
    """Saída de `auditar`: a decisão respeita a política?"""

    aprovada: bool
    problemas: list[str] = Field(default_factory=list)


class Acao(BaseModel):
    """Saída final: ação registrada (simulada) + rascunho de resposta."""

    tipo: str
    destino: Literal["automatico", "fila_humana", "nenhum"]
    payload: dict = Field(default_factory=dict)
    rascunho_resposta: str | None = None
