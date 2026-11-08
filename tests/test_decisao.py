from atendimento.servicos.decisao import decidir, regra_fixa
from atendimento.servicos.elegibilidade import avaliar


def _decidir(fab, c, ctx, msgs=()):
    return regra_fixa(c, "whatsapp") or decidir(c, ctx, avaliar(c, ctx, "X", list(msgs)))


def test_saude_sempre_humano_responsavel_tecnica(fab):
    d = regra_fixa(fab.classif("reacao_adversa", "rastreio_status"), "whatsapp")
    assert d.modo == "humano" and d.fila_destino == "responsavel_tecnica"


def test_reclame_aqui_sempre_humano(fab):
    assert regra_fixa(fab.classif("rastreio_status"), "reclame_aqui").fila_destino == "reclame_aqui"


def test_multi_motivo_com_um_humano_vai_inteiro_para_humano_preservando_acao(fab):
    d = _decidir(fab, fab.classif("cupom_promocao_nao_aplicou", "cobranca_duplicada"), fab.contexto())
    assert d.modo == "humano" and d.fila_destino == "comercial"
    assert any(a.tipo == "estorno" and a.modo == "automatico" for a in d.acoes)


def test_valor_acima_do_limite_vai_para_financeiro(fab):
    d = _decidir(fab, fab.classif("cobranca_duplicada"), fab.contexto(valor=450.0))
    assert d.modo == "humano" and d.fila_destino == "financeiro"


def test_rastreio_de_pedido_entregue_vai_para_logistica(fab):
    d = _decidir(fab, fab.classif("rastreio_status"), fab.contexto(status="entregue"))
    assert d.fila_destino == "logistica"


def test_atraso_em_transito_abre_chamado_automatico(fab):
    d = _decidir(fab, fab.classif("atraso"), fab.contexto(status="em_transito"))
    assert d.modo == "automatico" and d.acoes[0].tipo == "abrir_chamado_transportadora"


def test_indeterminado_pede_informacoes(fab):
    d = _decidir(fab, fab.classif("item_faltante"), fab.contexto(dias=5))
    assert d.modo == "automatico" and d.acoes[0].tipo == "solicitar_informacoes" and d.acoes[0].parametros["pedir"]
