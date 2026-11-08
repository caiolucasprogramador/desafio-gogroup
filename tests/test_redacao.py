from atendimento.dominio.schemas import AcaoPlanejada, Decisao
from atendimento.servicos.redacao import checar
from atendimento.servicos.respostas import redigir


def _decisao(*acoes):
    return Decisao(modo="automatico", acao_proposta="x", justificativa="", origem="regra",
                   acoes=[AcaoPlanejada(motivo=m, tipo=t, modo="automatico", parametros=p, justificativa="")
                          for m, t, p in acoes])


STATUS = ("rastreio_status", "informar_status", {"status": "em_transito", "transportadora": "Rota Express"})
ESTORNO = ("cobranca_duplicada", "estorno", {"observacoes": ["estorno em até 5 dias úteis (pix)"]})


def test_template_passa_nas_proprias_checagens():
    d = _decisao(STATUS, ESTORNO)
    t = redigir(d, "Ápice")
    assert checar(t, t, d) == []


def test_pega_promessa_nao_decidida():
    d = _decisao(STATUS)
    assert "prometeu 'estorno' sem decisão" in checar("Está em trânsito e faremos o estorno do frete.", "x", d)


def test_pega_assunto_omitido_e_prazo_perdido():
    d = _decisao(STATUS, ESTORNO)
    t = redigir(d, "Ápice")
    problemas = checar("Seu pedido está em trânsito. Equipe Ápice", t, d)
    assert "omitiu a ação 'estorno'" in problemas and any("'5'" in p for p in problemas)


def test_pega_dado_pessoal():
    d = _decisao(STATUS)
    assert "contém dado pessoal" in checar("Em trânsito. CPF 123.456.789-00", "x", d)
