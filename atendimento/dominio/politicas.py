"""Políticas vigentes (case_atendimento/parametros.md) como dados.

Cada motivo da taxonomia aponta para uma política (ou None = não há política escrita,
a decisão fica com o `decidir`/humano). As regras que AVALIAM a política estão em
servicos/elegibilidade.py.
"""
from dataclasses import dataclass

from atendimento.dominio.taxonomia import MOTIVOS


@dataclass(frozen=True)
class Politica:
    id: str
    texto: str                     # redação original da política
    acao: str                      # ação que a política autoriza
    prazo_dias: int | None = None  # contado do RECEBIMENTO
    exige_foto: bool = False


POLITICAS: dict[str, Politica] = {p.id: p for p in [
    Politica("arrependimento", "Arrependimento: até 7 dias do recebimento, reembolso integral (CDC, art. 49).",
             acao="reembolso_integral", prazo_dias=7),
    Politica("avaria_faltante", "Avaria, vazamento ou item faltante: reenvio sem custo, mediante foto, "
             "em até 7 dias do recebimento.", acao="reenvio_sem_custo", prazo_dias=7, exige_foto=True),
    Politica("troca_fragrancia", "Troca por insatisfação com fragrância: 1 troca por pedido, em até 30 dias, "
             "com no máximo 20% do produto utilizado.", acao="troca_fragrancia", prazo_dias=30),
    Politica("cobranca_duplicada", "Cobrança duplicada: estorno em até 2 faturas (cartão) ou 5 dias úteis (pix).",
             acao="estorno"),
    Politica("reacao_adversa", "Reação adversa: orientar a suspensão do uso, registrar no protocolo de "
             "cosmetovigilância (produto, lote, descrição e fotos) em até 24 horas e encaminhar para a "
             "responsável técnica. A troca do produto não substitui o registro.",
             acao="registro_cosmetovigilancia"),
    Politica("alteracao_endereco", "Alteração de endereço: possível somente antes da separação do pedido.",
             acao="alterar_endereco"),
    Politica("erro_personalizacao", "Erro de personalização Gocase: nova produção sem custo, mediante foto, "
             "em até 7 dias do recebimento.", acao="nova_producao", prazo_dias=7, exige_foto=True),
]}

# Motivo → política. Cancelamentos por desistência seguem o direito de arrependimento (CDC).
MOTIVO_PARA_POLITICA: dict[str, str | None] = {m: None for m in MOTIVOS} | {
    "arrependimento": "arrependimento",
    "compra_duplicada_cliente": "arrependimento",
    "cancelar_recomprar_cupom": "arrependimento",
    "avaria_vazamento": "avaria_faltante",
    "item_faltante": "avaria_faltante",
    "troca_fragrancia": "troca_fragrancia",
    "cobranca_duplicada": "cobranca_duplicada",
    "reacao_adversa": "reacao_adversa",
    "alteracao_endereco": "alteracao_endereco",
    "erro_personalizacao": "erro_personalizacao",
}

# Status de entrega que indicam que o pedido ainda NÃO foi separado.
STATUS_ANTES_SEPARACAO = {"aguardando_pagamento"}
STATUS_NAO_RECEBIDO = {"aguardando_pagamento", "em_separacao", "em_transito", "atrasado"}
