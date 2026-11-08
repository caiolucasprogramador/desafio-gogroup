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
    """Saída de `enriquecer`: fatos do pedido, do cliente e da conversa (sem LLM)."""

    order_id: str | None
    valor: float | None
    status_entrega: str | None
    transportadora: str | None
    dias_desde_pedido: int | None
    n_pedidos_cliente: int
    contatos_anteriores_cliente: int = Field(description="Conversas do cliente abertas antes desta.")
    contatos_anteriores_pedido: int = Field(description="Conversas sobre o mesmo pedido abertas antes desta.")
    aguardando_resposta: bool = Field(description="A última mensagem é do cliente (a empresa deve resposta).")
    horas_aguardando: float | None
    correcoes: list[str] = Field(
        default_factory=list,
        description="Ajustes na classificação feitos com base em fatos (ex.: rastreio_status → atraso).",
    )


class Prioridade(BaseModel):
    """Saída de `priorizar`: score determinístico e seus componentes (auditável)."""

    score: float = Field(ge=0, le=100)
    fatores: dict[str, float] = Field(description="Cada fator normalizado 0–100, antes do peso.")
    contribuicoes: dict[str, float] = Field(description="Pontos que cada fator somou ao score (fator × peso).")
    topo_da_fila: bool = Field(description="True para saúde: fura a fila independentemente do score.")


ResultadoElegibilidade = Literal["elegivel", "inelegivel", "indeterminado", "sem_politica"]


class AvaliacaoMotivo(BaseModel):
    """Avaliação de UM motivo contra a política correspondente."""

    motivo: str
    politica: str | None = Field(description="id em dominio/politicas.py; None se não há política escrita.")
    resultado: ResultadoElegibilidade
    acao_prevista: str | None = Field(description="Ação que a política autoriza (se elegível).")
    justificativa: str
    informacoes_faltantes: list[str] = Field(default_factory=list,
                                             description="O que pedir ao cliente/sistema para concluir.")
    observacoes: list[str] = Field(default_factory=list, description="Ex.: prazo de estorno, registro em 24h.")


class Elegibilidade(BaseModel):
    """Saída de `checar_elegibilidade`: cada motivo avaliado contra a política vigente."""

    avaliacoes: list[AvaliacaoMotivo]
    resultado: ResultadoElegibilidade = Field(description="Resultado do motivo principal.")


FilaHumana = Literal["responsavel_tecnica", "reclame_aqui", "financeiro", "logistica", "comercial", "atendimento"]


class AcaoPlanejada(BaseModel):
    """O que fazer com UM motivo da conversa."""

    motivo: str
    tipo: str = Field(description="Ex.: estorno, solicitar_informacoes, informar_status, encaminhar_humano.")
    modo: Literal["automatico", "humano"]
    fila: FilaHumana | None = Field(default=None, description="Fila humana de destino (se modo=humano).")
    parametros: dict = Field(default_factory=dict, description="Dados para executar a ação (valor, o que pedir...).")
    justificativa: str


class Decisao(BaseModel):
    """Saída de `regras_fixas` ou `decidir`."""

    modo: Literal["automatico", "humano"]
    acao_proposta: str = Field(description="Ação do motivo principal (resumo).")
    justificativa: str
    origem: Literal["regra", "llm"]
    fila_destino: FilaHumana | None = None
    acoes: list[AcaoPlanejada] = Field(default_factory=list, description="Uma ação por motivo da conversa.")


class Acao(BaseModel):
    """Saída final: ação registrada (simulada) + rascunho de resposta."""

    tipo: str
    destino: Literal["automatico", "fila_humana", "nenhum"]
    payload: dict = Field(default_factory=dict)
    rascunho_resposta: str | None = None
