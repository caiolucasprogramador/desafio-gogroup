"""Parâmetros de negócio (case_atendimento/parametros.md) e pesos de prioridade."""

# Data de extração dos dados: o "agora" da fila histórica.
DATA_REFERENCIA = "2026-09-30 00:00:00"

CUSTO_CONVERSA = {"whatsapp": 4.80, "email": 7.20, "reclame_aqui": 42.00}  # R$ por conversa
SLA_HORAS = {"whatsapp": 0.5, "email": 24.0, "reclame_aqui": 48.0}         # 1ª resposta

# Prioridade: cada fator é normalizado para 0–100; o score é a média ponderada.
PESOS_PRIORIDADE = {
    "gravidade": 0.40,   # o quê: GRAVIDADE dos motivos
    "canal": 0.15,       # onde: proporcional ao custo do canal (Reclame Aqui = 100)
    "sla": 0.15,         # quando: % do SLA consumido enquanto o cliente aguarda resposta
    "recontato": 0.15,   # cliente já voltou / conversa reaberta / outro contato sobre o mesmo pedido
    "valor": 0.10,       # quanto: valor do pedido (teto no percentil 90)
    "tom": 0.05,         # irritado ou urgente
}
assert abs(sum(PESOS_PRIORIDADE.values()) - 1) < 1e-9

# Gravidade da conversa = motivo mais grave + fração da soma dos demais (teto 100):
# um segundo problema pesa, mas vários problemas leves não superam um grave.
FATOR_MOTIVOS_SECUNDARIOS = 0.3

VALOR_TETO_PRIORIDADE = 163.0  # percentil 90 do valor dos pedidos (pedidos.csv)

# Decisão: acima deste valor (R$), reembolso/estorno/reenvio vai para revisão humana.
# Pedidos: mediana R$ 87, p90 R$ 163 → R$ 200 cobre ~95% dos pedidos.
LIMITE_VALOR_AUTOMATICO = 200.0
