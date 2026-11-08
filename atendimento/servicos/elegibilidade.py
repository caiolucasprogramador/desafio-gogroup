"""Elegibilidade: cada motivo da conversa avaliado contra a política vigente (sem LLM).

Princípio: só afirmamos "elegível"/"inelegível" com base em FATO. Quando falta um dado
(foto, data de recebimento, % usado), o resultado é "indeterminado" e listamos o que pedir.

Limitação dos dados: não há data de recebimento. Usamos um limite seguro:
recebido há no máximo `dias_desde_pedido` dias → se isso ≤ prazo, está dentro do prazo com certeza.
"""
import re

from atendimento.dominio.politicas import (
    MOTIVO_PARA_POLITICA, POLITICAS, STATUS_ANTES_SEPARACAO, STATUS_NAO_RECEBIDO, Politica,
)
from atendimento.dominio.schemas import AvaliacaoMotivo, Classificacao, ContextoPedido, Elegibilidade

RE_FOTO_ENVIADA = re.compile(r"segue (?:a )?foto|foto em anexo|enviei (?:a )?foto|mandei (?:a )?foto|anexei", re.I)
RE_PAGAMENTO = {"pix": re.compile(r"\bpix\b", re.I), "cartao": re.compile(r"cart[aã]o", re.I),
                "boleto": re.compile(r"\bboleto\b", re.I)}


def sinais_do_texto(mensagens_cliente: list[str]) -> dict:
    texto = " ".join(mensagens_cliente)
    return {
        "foto_enviada": bool(RE_FOTO_ENVIADA.search(texto)),
        "pagamentos": [nome for nome, r in RE_PAGAMENTO.items() if r.search(texto)],
    }


def situacao_prazo(ctx: ContextoPedido, prazo_dias: int) -> str:
    """'sem_pedido' | 'nao_recebido' | 'dentro' (certeza) | 'desconhecido' (falta data de recebimento)."""
    if not ctx.order_id or ctx.status_entrega is None:
        return "sem_pedido"
    if ctx.status_entrega in STATUS_NAO_RECEBIDO:
        return "nao_recebido"
    if ctx.dias_desde_pedido is not None and ctx.dias_desde_pedido <= prazo_dias:
        return "dentro"
    return "desconhecido"


def _av(motivo: str, pol: Politica | None, resultado: str, justificativa: str,
        faltantes: list[str] | None = None, obs: list[str] | None = None) -> AvaliacaoMotivo:
    return AvaliacaoMotivo(
        motivo=motivo, politica=pol.id if pol else None, resultado=resultado,
        acao_prevista=pol.acao if pol and resultado in ("elegivel", "indeterminado") else None,
        justificativa=justificativa, informacoes_faltantes=faltantes or [], observacoes=obs or [],
    )


# --- Uma função por política ------------------------------------------------------

def _arrependimento(motivo, pol, ctx, marca, sinais):
    s = situacao_prazo(ctx, pol.prazo_dias)
    if s == "sem_pedido":
        return _av(motivo, pol, "indeterminado", "Pedido não identificado.", ["número do pedido"])
    if s == "nao_recebido":
        return _av(motivo, pol, "elegivel", f"Pedido ainda não recebido ({ctx.status_entrega}): o prazo de "
                   "7 dias nem começou; cancelamento com reembolso integral.",
                   obs=["se já despachado, interceptar ou orientar recusa na entrega"])
    if s == "dentro":
        return _av(motivo, pol, "elegivel", f"Pedido feito há {ctx.dias_desde_pedido} dias: recebido há "
                   "no máximo isso, dentro dos 7 dias.")
    return _av(motivo, pol, "indeterminado", f"Pedido entregue e feito há {ctx.dias_desde_pedido} dias: "
               "depende da data de recebimento.", ["data de recebimento"])


def _com_foto_e_prazo(motivo, pol, ctx, marca, sinais):
    """Avaria/vazamento/item faltante e erro de personalização: prazo de 7 dias + foto."""
    if pol.id == "erro_personalizacao" and marca != "Gocase":
        return _av(motivo, pol, "inelegivel", f"Política de personalização vale só para Gocase (marca: {marca}).")
    s = situacao_prazo(ctx, pol.prazo_dias)
    if s == "sem_pedido":
        return _av(motivo, pol, "indeterminado", "Pedido não identificado.", ["número do pedido"])
    if s == "nao_recebido":
        return _av(motivo, pol, "indeterminado", f"Pedido consta como '{ctx.status_entrega}', mas o cliente "
                   "relata problema no produto recebido: verificar entrega parcial.", ["confirmação da entrega"])
    faltantes = []
    if s == "desconhecido":
        faltantes.append("data de recebimento")
    if not sinais["foto_enviada"]:
        faltantes.append("foto do produto e da embalagem")
    if faltantes:
        return _av(motivo, pol, "indeterminado", "Condições da política ainda não comprovadas.", faltantes)
    return _av(motivo, pol, "elegivel", f"Dentro de 7 dias (pedido há {ctx.dias_desde_pedido} dias) e foto enviada.")


def _troca_fragrancia(motivo, pol, ctx, marca, sinais):
    s = situacao_prazo(ctx, pol.prazo_dias)
    if s == "sem_pedido":
        return _av(motivo, pol, "indeterminado", "Pedido não identificado.", ["número do pedido"])
    if s == "nao_recebido":
        return _av(motivo, pol, "inelegivel", f"Pedido ainda não recebido ({ctx.status_entrega}): não há o que trocar.")
    faltantes = ["percentual do produto já utilizado (máx. 20%)"]
    if s == "desconhecido":
        faltantes.append("data de recebimento")
    obs = ["verificar se já houve troca neste pedido (limite: 1)"] if ctx.contatos_anteriores_pedido else []
    return _av(motivo, pol, "indeterminado", "Prazo de 30 dias ok pelo limite seguro; falta confirmar o uso.",
               faltantes, obs)


def _cobranca_duplicada(motivo, pol, ctx, marca, sinais):
    prazos = {"cartao": "estorno em até 2 faturas", "pix": "estorno em até 5 dias úteis"}
    obs = ["confirmar a duplicidade no sistema financeiro antes do estorno"]
    obs += [prazos[p] + f" ({p})" for p in sinais["pagamentos"] if p in prazos]
    faltantes = [] if any(p in prazos for p in sinais["pagamentos"]) else ["forma de pagamento (cartão ou pix)"]
    return _av(motivo, pol, "elegivel", "Política garante estorno da cobrança em duplicidade.", faltantes, obs)


def _reacao_adversa(motivo, pol, ctx, marca, sinais):
    faltantes = ["lote do produto"] + ([] if sinais["foto_enviada"] else ["fotos da reação"])
    obs = ["orientar suspensão imediata do uso", "registrar na cosmetovigilância em até 24h",
           "encaminhar para a responsável técnica", "troca do produto NÃO substitui o registro"]
    return _av(motivo, pol, "elegivel", "Obrigatório: protocolo de cosmetovigilância.", faltantes, obs)


def _alteracao_endereco(motivo, pol, ctx, marca, sinais):
    if not ctx.order_id or ctx.status_entrega is None:
        return _av(motivo, pol, "indeterminado", "Pedido não identificado.", ["número do pedido"])
    if ctx.status_entrega in STATUS_ANTES_SEPARACAO:
        return _av(motivo, pol, "elegivel", f"Pedido ainda não separado ({ctx.status_entrega}).",
                   ["novo endereço completo"])
    return _av(motivo, pol, "inelegivel", f"Pedido já em '{ctx.status_entrega}': separação já iniciada ou concluída.",
               obs=["oferecer alternativas: retirada na transportadora ou reenvio após devolução"])


REGRAS = {
    "arrependimento": _arrependimento,
    "avaria_faltante": _com_foto_e_prazo,
    "erro_personalizacao": _com_foto_e_prazo,
    "troca_fragrancia": _troca_fragrancia,
    "cobranca_duplicada": _cobranca_duplicada,
    "reacao_adversa": _reacao_adversa,
    "alteracao_endereco": _alteracao_endereco,
}


def avaliar(c: Classificacao, ctx: ContextoPedido, marca: str, mensagens_cliente: list[str]) -> Elegibilidade:
    sinais = sinais_do_texto(mensagens_cliente)
    avaliacoes = []
    for motivo in dict.fromkeys(m.motivo for m in c.motivos):
        pol_id = MOTIVO_PARA_POLITICA[motivo]
        if pol_id is None:
            avaliacoes.append(_av(motivo, None, "sem_politica", "Não há política escrita para este motivo."))
        else:
            avaliacoes.append(REGRAS[pol_id](motivo, POLITICAS[pol_id], ctx, marca, sinais))
    principal = next((a for a in avaliacoes if a.motivo == c.motivo_principal), None)
    return Elegibilidade(avaliacoes=avaliacoes, resultado=principal.resultado if principal else "sem_politica")


def resumir(e: Elegibilidade) -> str:
    partes = []
    for a in e.avaliacoes:
        txt = f"{a.motivo}={a.resultado}"
        if a.informacoes_faltantes:
            txt += f" (faltam: {', '.join(a.informacoes_faltantes)})"
        partes.append(txt)
    return "; ".join(partes) or "nenhum motivo"
