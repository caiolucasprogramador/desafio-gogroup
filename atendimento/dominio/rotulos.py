"""Rótulos em português para exibir códigos internos (categoria, motivo, canal, ação, fila).

Usados no diagnóstico agregado (scripts/gerar_diagnostico.py → public/diagnostico.json).
"""
from atendimento.dominio.taxonomia import MOTIVOS, TAXONOMIA

CATEGORIAS: dict[str, str] = {
    "saude": "Saúde",
    "entrega": "Entrega",
    "pedido_incompleto_danificado": "Pedido incompleto ou danificado",
    "financeiro": "Financeiro",
    "cancelamento_troca": "Cancelamento e troca",
    "promocao": "Promoção e cupom",
    "produto": "Produto",
    "outros": "Outros",
}

MOTIVOS_ROTULO: dict[str, str] = {
    "reacao_adversa": "Reação adversa",
    "duvida_saude": "Dúvida de saúde",
    "rastreio_status": "Dúvida sobre rastreio",
    "atraso": "Atraso na entrega",
    "alteracao_endereco": "Alteração de endereço",
    "item_faltante": "Item faltante",
    "brinde_faltante": "Brinde faltante",
    "avaria_vazamento": "Avaria ou vazamento",
    "erro_personalizacao": "Erro de personalização",
    "cobranca_duplicada": "Cobrança duplicada",
    "cobranca_nao_reconhecida": "Cobrança não reconhecida",
    "pagamento_nao_confirmado": "Pagamento não confirmado",
    "cashback": "Cashback",
    "arrependimento": "Arrependimento",
    "compra_duplicada_cliente": "Compra duplicada pelo cliente",
    "cancelar_recomprar_cupom": "Cancelar para recomprar com cupom",
    "troca_fragrancia": "Troca de fragrância",
    "troca_outros": "Troca (exceto fragrância)",
    "cupom_promocao_nao_aplicou": "Cupom não aplicado",
    "frete_gratis": "Frete grátis não aplicado",
    "insatisfacao_produto": "Insatisfação com o produto",
    "duvida_produto": "Dúvida sobre produto",
    "elogio": "Elogio",
    "sem_conteudo": "Abandono no bot",
    "outro": "Outro",
}

CANAIS: dict[str, str] = {"whatsapp": "WhatsApp", "email": "E-mail", "reclame_aqui": "Reclame Aqui"}

ACOES: dict[str, str] = {
    "solicitar_informacoes": "Pedir informação ao cliente",
    "abrir_chamado_transportadora": "Abrir chamado na transportadora",
    "informar_status": "Informar status do pedido",
    "reembolso_integral": "Reembolso integral",
    "informar_inelegibilidade": "Explicar que a política não cobre",
    "estorno": "Estorno de cobrança duplicada",
    "agradecer": "Agradecer elogio",
    "nova_producao": "Nova produção da personalização",
    "reenvio_sem_custo": "Reenvio sem custo",
    "troca_fragrancia": "Troca de fragrância",
    "alterar_endereco": "Alterar endereço",
}

FILAS: dict[str, str] = {
    "atendimento": "Atendimento",
    "reclame_aqui": "Reclame Aqui",
    "comercial": "Comercial",
    "financeiro": "Financeiro",
    "responsavel_tecnica": "Responsável técnica",
    "logistica": "Logística",
}

assert set(CATEGORIAS) == set(TAXONOMIA), "toda categoria precisa de rótulo"
assert set(MOTIVOS_ROTULO) == set(MOTIVOS), "todo motivo precisa de rótulo"
