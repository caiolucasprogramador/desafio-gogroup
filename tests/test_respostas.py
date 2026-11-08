from atendimento.dominio.schemas import AcaoPlanejada, Decisao
from atendimento.servicos.respostas import TEMPLATES, redigir

TIPOS_AUTOMATICOS = {"informar_status", "abrir_chamado_transportadora", "solicitar_informacoes",
                     "informar_inelegibilidade", "estorno", "reembolso_integral", "reenvio_sem_custo",
                     "nova_producao", "alterar_endereco", "agradecer"}


def test_todo_tipo_automatico_tem_template():
    assert TIPOS_AUTOMATICOS <= set(TEMPLATES)


def test_rascunho_tem_um_paragrafo_por_motivo():
    acoes = [AcaoPlanejada(motivo="atraso", tipo="abrir_chamado_transportadora", modo="automatico",
                           parametros={"status": "em_transito", "transportadora": "Rota Express"}, justificativa=""),
             AcaoPlanejada(motivo="cobranca_duplicada", tipo="estorno", modo="automatico",
                           parametros={"observacoes": ["estorno em até 5 dias úteis (pix)"]}, justificativa="")]
    d = Decisao(modo="automatico", acao_proposta="estorno", justificativa="", origem="regra", acoes=acoes)
    texto = redigir(d, "Ápice")
    assert "transportadora" in texto and "estorno" in texto and "5 dias úteis" in texto
    assert texto.count("\n\n") == 3 and texto.endswith("Equipe Ápice")


def test_motivos_com_mesma_acao_nao_repetem_paragrafo():
    chamado = dict(tipo="abrir_chamado_transportadora", modo="automatico",
                   parametros={"status": "atrasado"}, justificativa="")
    acoes = [AcaoPlanejada(motivo="atraso", **chamado), AcaoPlanejada(motivo="rastreio_status", **chamado)]
    d = Decisao(modo="automatico", acao_proposta="abrir_chamado_transportadora", justificativa="",
                origem="regra", acoes=acoes)
    assert redigir(d, "Gocase").count("chamado prioritário") == 1
