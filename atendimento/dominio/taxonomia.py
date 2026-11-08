"""Taxonomia de motivos de contato: fonte única para gabarito, schema e classificadores.

Dois níveis: categoria (visão de painel) → motivo (ligado a política e ação).
"""

TAXONOMIA: dict[str, dict[str, str]] = {
    "saude": {
        "reacao_adversa": "Cliente relata reação física após usar o produto (coceira, queimação, inchaço, alergia).",
        "duvida_saude": "Pergunta de segurança de uso: gravidez, amamentação, crianças, condições de saúde.",
    },
    "entrega": {
        "rastreio_status": "Quer saber onde está o pedido ou o código de rastreio, sem dizer que o prazo venceu.",
        "atraso": "Prazo de entrega prometido já venceu ou cliente afirma atraso.",
        "alteracao_endereco": "Quer corrigir ou alterar o endereço de entrega.",
    },
    "pedido_incompleto_danificado": {
        "item_faltante": "Produto comprado não veio no pedido (kit incompleto, veio menos itens).",
        "brinde_faltante": "Brinde ou mimo de promoção não veio.",
        "avaria_vazamento": "Produto chegou quebrado, vazando, aberto, amassado ou com lacre violado.",
        "erro_personalizacao": "Personalização Gocase errada: nome, foto, iniciais, impressão borrada ou torta.",
    },
    "financeiro": {
        "cobranca_duplicada": "Empresa cobrou duas vezes o mesmo pedido (cartão, pix, boleto + cartão).",
        "cobranca_nao_reconhecida": "Cobrança que o cliente não reconhece.",
        "pagamento_nao_confirmado": "Pagou (pix/boleto) e o pedido segue aguardando pagamento.",
        "cashback": "Cashback não recebido ou com problema.",
    },
    "cancelamento_troca": {
        "arrependimento": "Desistiu da compra e quer cancelar/devolver com reembolso.",
        "compra_duplicada_cliente": "Cliente comprou duas vezes por engano e quer cancelar um pedido.",
        "cancelar_recomprar_cupom": "Quer cancelar para refazer a compra com cupom ou promoção.",
        "troca_fragrancia": "Quer trocar por outra fragrância.",
        "troca_outros": "Quer trocar por outro motivo (tamanho, modelo, não era o esperado).",
    },
    "promocao": {
        "cupom_promocao_nao_aplicou": "Cupom ou promoção do site não funcionou.",
        "frete_gratis": "Frete grátis não foi aplicado.",
    },
    "produto": {
        "insatisfacao_produto": "Reclama da qualidade/experiência do produto (cheiro, fixação, textura) sem pedir troca.",
        "duvida_produto": "Dúvida de uso, composição ou indicação que não envolve saúde (vegano, tipo de pele, validade).",
    },
    "outros": {
        "elogio": "Elogio ou agradecimento sem outro pedido.",
        "sem_conteudo": "Cliente não escreveu nada (abandono no bot).",
        "outro": "Nenhum dos motivos acima.",
    },
}

MOTIVO_PARA_CATEGORIA: dict[str, str] = {
    motivo: categoria for categoria, motivos in TAXONOMIA.items() for motivo in motivos
}
MOTIVOS: list[str] = list(MOTIVO_PARA_CATEGORIA)

# Gravidade de cada motivo (0–100). Fonte única para:
# - motivo_principal (o mais grave da conversa; empate → o primeiro mencionado);
# - componente de gravidade do score do nó `priorizar`.
GRAVIDADE: dict[str, int] = {
    # Saúde: risco ao cliente e prazo regulatório (cosmetovigilância em 24h)
    "reacao_adversa": 100, "duvida_saude": 90,
    # Dinheiro do cliente retido indevidamente
    "cobranca_duplicada": 80, "cobranca_nao_reconhecida": 80,
    "pagamento_nao_confirmado": 70,
    # Direito garantido / prazo curto de política
    "arrependimento": 60, "compra_duplicada_cliente": 60,
    # Pedido com problema físico ou de entrega
    "avaria_vazamento": 55, "item_faltante": 55, "erro_personalizacao": 55,
    "alteracao_endereco": 50, "atraso": 50,
    # Troca, cancelamento opcional, benefícios
    "troca_fragrancia": 40, "troca_outros": 40,
    "cancelar_recomprar_cupom": 35, "brinde_faltante": 35, "cashback": 35,
    # Informação e experiência
    "rastreio_status": 25, "cupom_promocao_nao_aplicou": 25, "frete_gratis": 25,
    "insatisfacao_produto": 20, "duvida_produto": 15,
    "outro": 10, "elogio": 5, "sem_conteudo": 0,
}
assert set(GRAVIDADE) == set(MOTIVOS), "todo motivo precisa de gravidade"

# Motivos que sempre escalam para humano (decisão de negócio).
SEMPRE_HUMANO: set[str] = {"reacao_adversa", "duvida_saude"}

TONS = ("neutro", "irritado", "urgente")
