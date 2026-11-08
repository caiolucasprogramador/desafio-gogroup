"""Rascunho da resposta ao cliente a partir das ações decididas (templates, sem LLM).

Um parágrafo por motivo: conversa com vários assuntos recebe resposta para TODOS
(a falha mais comum que encontramos no atendimento humano era responder só o primeiro).
Os templates usam apenas os parâmetros da ação — nunca o texto do cliente — então
nenhum dado pessoal vaza para a resposta.
"""
from atendimento.dominio.schemas import AcaoPlanejada, Decisao

STATUS_LEGIVEL = {
    "aguardando_pagamento": "aguardando a confirmação do pagamento",
    "em_separacao": "em separação no nosso centro de distribuição",
    "em_transito": "em trânsito",
    "atrasado": "com atraso na entrega",
    "entregue": "entregue",
}

ITEM_LEGIVEL = {
    "foto do produto e da embalagem": "uma foto do produto e da embalagem",
    "data de recebimento": "a data em que você recebeu o pedido",
    "número do pedido": "o número do pedido",
    "percentual do produto já utilizado (máx. 20%)": "quanto do produto já foi usado (aceitamos troca com até 20% de uso)",
    "confirmação da entrega": "a confirmação de quais itens chegaram",
    "novo endereço completo": "o novo endereço completo, com CEP",
    "forma de pagamento (cartão ou pix)": "a forma de pagamento usada (cartão ou pix)",
    "lote do produto": "o número do lote do produto",
    "fotos da reação": "fotos da reação",
}

FINALIDADE = {  # para que servem as informações pedidas (acao_se_confirmado)
    "reenvio_sem_custo": "para enviarmos o item novamente, sem custo",
    "nova_producao": "para produzirmos uma nova peça, sem custo",
    "reembolso_integral": "para concluirmos o cancelamento com reembolso integral",
    "troca_fragrancia": "para seguirmos com a troca de fragrância",
    "alterar_endereco": "para alterarmos o endereço",
}


def _lista(itens: list[str]) -> str:
    itens = [ITEM_LEGIVEL.get(i, i) for i in itens]
    return itens[0] if len(itens) == 1 else ", ".join(itens[:-1]) + " e " + itens[-1]


def _prazo_estorno(obs: list[str]) -> str:
    prazos = [o.split(" (")[0] for o in obs if o.startswith("estorno em")]
    return f" O valor volta para você {prazos[0].replace('estorno ', '')}." if prazos else ""


def _informar_status(a: AcaoPlanejada) -> str:
    p = a.parametros
    return (f"Verificamos seu pedido: ele está {STATUS_LEGIVEL.get(p.get('status'), p.get('status'))}"
            f"{' com a ' + p['transportadora'] if p.get('transportadora') else ''}. "
            "Assim que houver nova movimentação, você é avisado pelo rastreio.")


def _abrir_chamado(a: AcaoPlanejada) -> str:
    p = a.parametros
    return (f"Sentimos muito pela demora. Seu pedido está {STATUS_LEGIVEL.get(p.get('status'), p.get('status'))}"
            f"{' com a ' + p['transportadora'] if p.get('transportadora') else ''}, e já abrimos um chamado "
            "prioritário com a transportadora. Retornamos com uma posição em até 48 horas.")


def _solicitar(a: AcaoPlanejada) -> str:
    fim = FINALIDADE.get(a.parametros.get("acao_se_confirmado"), "para darmos andamento à sua solicitação")
    return f"Para resolvermos, precisamos que você nos envie {_lista(a.parametros.get('pedir', []))}, {fim}."


def _inelegivel(a: AcaoPlanejada) -> str:
    pol = a.parametros.get("politica")
    if pol == "alteracao_endereco":
        return ("Infelizmente seu pedido já entrou em separação e não é mais possível alterar o endereço. "
                "Como alternativa, você pode retirá-lo na agência da transportadora ou, se ele retornar, "
                "reenviamos para o endereço correto.")
    if pol == "troca_fragrancia":
        return "A troca de fragrância pode ser solicitada assim que você receber o pedido, em até 30 dias."
    if pol == "erro_personalizacao":
        return "A nova produção sem custo vale para produtos personalizados Gocase; vamos verificar seu caso."
    return "Pela nossa política, essa solicitação não se aplica ao seu pedido neste momento."


TEMPLATES = {
    "informar_status": _informar_status,
    "abrir_chamado_transportadora": _abrir_chamado,
    "solicitar_informacoes": _solicitar,
    "informar_inelegibilidade": _inelegivel,
    "estorno": lambda a: ("Identificamos a cobrança em duplicidade e já solicitamos o estorno ao nosso financeiro."
                          + _prazo_estorno(a.parametros.get("observacoes", []))),
    "reembolso_integral": lambda a: ("Seu cancelamento foi solicitado e o reembolso será integral"
                                     + (f", no valor de R$ {a.parametros['valor']:.2f}".replace(".", ",")
                                        if a.parametros.get("valor") else "") + "."),
    "reenvio_sem_custo": lambda a: "Vamos reenviar o item sem nenhum custo para você. O novo código de rastreio chega por aqui.",
    "nova_producao": lambda a: "Vamos produzir uma nova peça com a personalização correta, sem custo para você.",
    "alterar_endereco": lambda a: ("Seu pedido ainda não foi separado, então conseguimos alterar o endereço. "
                                   f"Por favor, nos envie {_lista(a.parametros.get('pedir', ['novo endereço completo']))}."),
    "agradecer": lambda a: "Ficamos muito felizes com o seu retorno, obrigado pelo carinho! 💜",
}


def redigir(decisao: Decisao, marca: str) -> str:
    """Resposta completa: saudação + um parágrafo por ação + assinatura."""
    paragrafos = [TEMPLATES[a.tipo](a) for a in decisao.acoes]  # KeyError = tipo sem template (teste cobre)
    return "\n\n".join(["Olá! Obrigado por falar com a gente.", *paragrafos, f"Equipe {marca or 'Gocase'}"])
