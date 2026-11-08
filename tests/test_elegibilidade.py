from atendimento.servicos.elegibilidade import avaliar

FOTO = ["chegou quebrado", "segue a foto em anexo"]


def _res(e, motivo):
    return next(a for a in e.avaliacoes if a.motivo == motivo)


def test_avaria_dentro_do_prazo_com_foto_e_elegivel(fab):
    e = avaliar(fab.classif("avaria_vazamento"), fab.contexto(dias=5), "Ápice", FOTO)
    assert e.resultado == "elegivel" and _res(e, "avaria_vazamento").acao_prevista == "reenvio_sem_custo"


def test_avaria_sem_foto_pede_foto(fab):
    e = avaliar(fab.classif("avaria_vazamento"), fab.contexto(dias=5), "Ápice", ["chegou quebrado"])
    assert e.resultado == "indeterminado"
    assert "foto do produto e da embalagem" in _res(e, "avaria_vazamento").informacoes_faltantes


def test_entregue_ha_mais_de_7_dias_depende_da_data_de_recebimento(fab):
    e = avaliar(fab.classif("arrependimento"), fab.contexto(dias=12), "Ápice", ["desisti"])
    assert e.resultado == "indeterminado" and "data de recebimento" in _res(e, "arrependimento").informacoes_faltantes


def test_arrependimento_antes_de_receber_e_elegivel(fab):
    assert avaliar(fab.classif("arrependimento"), fab.contexto(status="em_transito", dias=20), "X", []).resultado == "elegivel"


def test_personalizacao_fora_da_gocase_e_inelegivel(fab):
    assert avaliar(fab.classif("erro_personalizacao"), fab.contexto(), "Ápice", FOTO).resultado == "inelegivel"


def test_endereco_com_pedido_separado_e_inelegivel(fab):
    assert avaliar(fab.classif("alteracao_endereco"), fab.contexto(status="em_transito"), "X", []).resultado == "inelegivel"
    assert avaliar(fab.classif("alteracao_endereco"), fab.contexto(status="aguardando_pagamento"), "X", []).resultado == "elegivel"


def test_cobranca_duplicada_informa_prazo_pela_forma_de_pagamento(fab):
    e = avaliar(fab.classif("cobranca_duplicada"), fab.contexto(), "X", ["paguei com pix e saiu duas vezes"])
    assert "estorno em até 5 dias úteis (pix)" in _res(e, "cobranca_duplicada").observacoes


def test_cada_motivo_e_avaliado(fab):
    e = avaliar(fab.classif("cupom_promocao_nao_aplicou", "cobranca_duplicada"), fab.contexto(), "X", [])
    assert {a.motivo: a.resultado for a in e.avaliacoes} == {
        "cupom_promocao_nao_aplicou": "sem_politica", "cobranca_duplicada": "elegivel"}
