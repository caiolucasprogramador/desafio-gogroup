"""Decisão determinística: o que fazer com cada motivo, e se a conversa resolve sozinha ou vai a humano.

Duas camadas:
1. regra_fixa(): casos que NUNCA são automáticos (saúde, Reclame Aqui). Roda antes de tudo.
2. decidir(): tabela de decisão por motivo, usando a elegibilidade (políticas) e, para motivos
   sem política escrita, regras operacionais baseadas em fatos (ex.: status de entrega).

Conversa só é automática se TODOS os motivos tiverem ação automática;
senão vai inteira para humano, levando as ações sugeridas dos demais motivos.
"""
from atendimento.dominio.parametros import LIMITE_VALOR_AUTOMATICO
from atendimento.dominio.schemas import (
    AcaoPlanejada, AvaliacaoMotivo, Classificacao, ContextoPedido, Decisao, Elegibilidade,
)
from atendimento.dominio.taxonomia import GRAVIDADE, SEMPRE_HUMANO

# Motivos sem política escrita e sem regra operacional → fila humana responsável.
FILA_SEM_REGRA = {
    "duvida_saude": ("responsavel_tecnica", "Pergunta de segurança de uso: só a responsável técnica responde."),
    "duvida_produto": ("atendimento", "Não há base de conhecimento de produto para responder com segurança."),
    "brinde_faltante": ("comercial", "Não há política de reenvio de brinde; decisão comercial."),
    "insatisfacao_produto": ("atendimento", "Não há política de compensação por insatisfação."),
    "troca_outros": ("atendimento", "Troca fora da política de fragrância: avaliar caso a caso."),
    "pagamento_nao_confirmado": ("financeiro", "Verificar baixa do pagamento no sistema."),
    "cobranca_nao_reconhecida": ("financeiro", "Possível fraude ou cobrança indevida: análise do financeiro."),
    "cashback": ("comercial", "Regras de cashback não estão nas políticas."),
    "cupom_promocao_nao_aplicou": ("comercial", "Validar regras da promoção/cupom."),
    "frete_gratis": ("comercial", "Validar regra de frete grátis."),
    "outro": ("atendimento", "Motivo não mapeado."),
}
ACOES_COM_CUSTO = {"reembolso_integral", "estorno", "reenvio_sem_custo", "nova_producao"}


def _auto(motivo, tipo, justificativa, **parametros) -> AcaoPlanejada:
    return AcaoPlanejada(motivo=motivo, tipo=tipo, modo="automatico", parametros=parametros, justificativa=justificativa)


def _humano(motivo, fila, justificativa, tipo="encaminhar_humano", **parametros) -> AcaoPlanejada:
    return AcaoPlanejada(motivo=motivo, tipo=tipo, modo="humano", fila=fila, parametros=parametros,
                         justificativa=justificativa)


# --- Camada 1: regras fixas ---------------------------------------------------------

def regra_fixa(c: Classificacao, canal: str) -> Decisao | None:
    """Saúde e Reclame Aqui nunca são automáticos. None = nenhuma regra fixa se aplica."""
    if saude := {m.motivo for m in c.motivos} & SEMPRE_HUMANO:
        return Decisao(modo="humano", origem="regra", fila_destino="responsavel_tecnica",
                       acao_proposta="encaminhar_responsavel_tecnica",
                       justificativa=f"Saúde ({', '.join(sorted(saude))}): exige responsável técnica "
                                     "e registro de cosmetovigilância em até 24h.")
    if canal == "reclame_aqui":
        return Decisao(modo="humano", origem="regra", fila_destino="reclame_aqui",
                       acao_proposta="resposta_publica_analista",
                       justificativa="Reclame Aqui: resposta pública e risco reputacional.")
    return None


# --- Camada 2: tabela de decisão por motivo -------------------------------------------

def _entrega(motivo: str, ctx: ContextoPedido) -> AcaoPlanejada:
    """Rastreio/atraso: não há política escrita, mas há fatos (status, transportadora)."""
    status, transp = ctx.status_entrega, ctx.transportadora
    if status is None:
        return _auto(motivo, "solicitar_informacoes", "Pedido não identificado.", pedir=["número do pedido"])
    if status == "entregue":
        return _humano(motivo, "logistica", "Pedido consta como entregue, mas o cliente não o tem: "
                       "possível extravio ou entrega em local errado.", status=status, transportadora=transp)
    if status == "atrasado" or motivo == "atraso":
        return _auto(motivo, "abrir_chamado_transportadora",
                     f"Pedido {status} com a {transp}: abrir chamado e informar o cliente.",
                     status=status, transportadora=transp)
    return _auto(motivo, "informar_status", f"Pedido {status} com a {transp}: informar a situação.",
                 status=status, transportadora=transp)


def _por_elegibilidade(av: AvaliacaoMotivo, ctx: ContextoPedido) -> AcaoPlanejada:
    if av.resultado == "indeterminado":
        return _auto(av.motivo, "solicitar_informacoes", av.justificativa, pedir=av.informacoes_faltantes,
                     acao_se_confirmado=av.acao_prevista)
    if av.resultado == "inelegivel":
        return _auto(av.motivo, "informar_inelegibilidade", av.justificativa, politica=av.politica,
                     alternativas=av.observacoes)
    # elegível
    acao = av.acao_prevista
    if acao == "registro_cosmetovigilancia":  # normalmente já capturado pela regra fixa
        return _humano(av.motivo, "responsavel_tecnica", av.justificativa, tipo=acao, checklist=av.observacoes)
    if acao in ACOES_COM_CUSTO and (ctx.valor is None or ctx.valor > LIMITE_VALOR_AUTOMATICO):
        return _humano(av.motivo, "financeiro", f"Elegível, mas valor R$ {ctx.valor} acima do limite automático "
                       f"(R$ {LIMITE_VALOR_AUTOMATICO:.0f}).", tipo=acao, valor=ctx.valor)
    params = {"valor": ctx.valor, "observacoes": av.observacoes}
    if av.informacoes_faltantes:
        params["pedir"] = av.informacoes_faltantes  # ex.: novo endereço completo
    return _auto(av.motivo, acao, av.justificativa, **params)


def decidir_motivo(av: AvaliacaoMotivo, ctx: ContextoPedido) -> AcaoPlanejada:
    if av.politica is not None:
        return _por_elegibilidade(av, ctx)
    if av.motivo in ("rastreio_status", "atraso"):
        return _entrega(av.motivo, ctx)
    if av.motivo == "elogio":
        return _auto(av.motivo, "agradecer", "Elogio: agradecer.")
    fila, motivo_fila = FILA_SEM_REGRA.get(av.motivo, ("atendimento", "Sem regra definida."))
    return _humano(av.motivo, fila, motivo_fila)


def decidir(c: Classificacao, ctx: ContextoPedido, e: Elegibilidade) -> Decisao:
    acoes = [decidir_motivo(av, ctx) for av in e.avaliacoes]
    if not acoes:
        return Decisao(modo="humano", origem="regra", fila_destino="atendimento", acao_proposta="revisao_manual",
                       justificativa="Nenhum motivo identificado.")
    principal = next((a for a in acoes if a.motivo == c.motivo_principal), acoes[0])
    humanas = [a for a in acoes if a.modo == "humano"]
    if not humanas:
        return Decisao(modo="automatico", origem="regra", acao_proposta=principal.tipo, acoes=acoes,
                       justificativa="Todos os motivos têm ação automática: " +
                                     "; ".join(f"{a.motivo}→{a.tipo}" for a in acoes))
    mais_grave = max(humanas, key=lambda a: GRAVIDADE[a.motivo])
    return Decisao(modo="humano", origem="regra", acao_proposta=principal.tipo, acoes=acoes,
                   fila_destino=mais_grave.fila,
                   justificativa=f"{mais_grave.motivo} exige humano ({mais_grave.justificativa})" +
                                 (f"; ações sugeridas p/ demais motivos: {len(acoes) - len(humanas)}"
                                  if len(acoes) > len(humanas) else ""))
