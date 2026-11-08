"""Exemplos prontos para a tela "Testar o agente".

Escritos à mão para a demonstração: NÃO vêm das conversas do case (que não podem ser
compartilhadas). Cada um exercita um caminho diferente do grafo.
"""

EXEMPLOS = [
    {
        "id": "arrependimento",
        "titulo": "Arrependimento recente",
        "caminho": "reembolso automático",
        "mensagens": ["Oi! Fiz o pedido anteontem e me arrependi, quero cancelar e receber meu dinheiro de volta."],
        "pedido": {"canal": "whatsapp", "marca": "Kokeshi", "status_entrega": "em_transito",
                   "dias_desde_pedido": 2, "valor": 129.90, "contatos_anteriores_pedido": 0},
    },
    {
        "id": "reacao",
        "titulo": "Reação alérgica",
        "caminho": "saúde → responsável técnica",
        "mensagens": ["Usei o sérum ontem e meu rosto ficou vermelho, ardendo e com bolinhas. O que eu faço?"],
        "pedido": {"canal": "whatsapp", "marca": "Kokeshi", "status_entrega": "entregue",
                   "dias_desde_pedido": 10, "valor": 89.90, "contatos_anteriores_pedido": 0},
    },
    {
        "id": "cobranca",
        "titulo": "Cobrança duplicada",
        "caminho": "estorno automático",
        "mensagens": ["Fui cobrada duas vezes no cartão pelo mesmo pedido!!", "Quero o estorno de uma das cobranças."],
        "pedido": {"canal": "email", "marca": "Ápice", "status_entrega": "em_separacao",
                   "dias_desde_pedido": 3, "valor": 149.00, "contatos_anteriores_pedido": 0},
    },
    {
        "id": "atraso",
        "titulo": "Atraso + recontato",
        "caminho": "chamado na transportadora",
        "mensagens": ["Meu pedido já devia ter chegado faz uma semana e o rastreio não atualiza.",
                      "Já é a terceira vez que falo com vocês sobre isso."],
        "pedido": {"canal": "whatsapp", "marca": "Gocase", "status_entrega": "atrasado",
                   "dias_desde_pedido": 18, "valor": 199.90, "contatos_anteriores_pedido": 2},
    },
    {
        "id": "dois_assuntos",
        "titulo": "Dois assuntos",
        "caminho": "humano com ação sugerida",
        "mensagens": ["Minha capinha chegou com o nome errado: pedi 'Ana' e veio 'Ama'. Segue a foto.",
                      "E o cupom PRIMEIRA10 também não foi aplicado na compra."],
        "pedido": {"canal": "whatsapp", "marca": "Gocase", "status_entrega": "entregue",
                   "dias_desde_pedido": 4, "valor": 99.90, "contatos_anteriores_pedido": 0},
    },
    {
        "id": "reclame_aqui",
        "titulo": "Reclame Aqui",
        "caminho": "regra fixa → humano",
        "mensagens": ["Comprei há 20 dias e até agora nada. Ninguém responde, péssimo atendimento."],
        "pedido": {"canal": "reclame_aqui", "marca": "Lescent", "status_entrega": "atrasado",
                   "dias_desde_pedido": 20, "valor": 159.90, "contatos_anteriores_pedido": 1},
    },
]
