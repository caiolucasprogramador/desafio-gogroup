"""Rótulos propostos (Claude) para o gabarito — a revisão humana fica na coluna `revisado`.

Regras de rotulagem:
- motivo_principal = o motivo mais grave (taxonomia.GRAVIDADE); empate → primeiro mencionado.
- rastreio_status vs atraso: só é atraso se o cliente afirma prazo vencido.
- recontato: "De novo aqui", "Já é a Nª vez", "Ninguém me respondeu ainda!".
- tom: irritado (reclamação agressiva, sarcasmo, "absurdo", "Ninguém me respondeu"),
  urgente (pede solução hoje, presente, sintoma persistente), senão neutro.
"""
from pathlib import Path
import pandas as pd
from atendimento.servicos.classificacao import motivo_principal
from atendimento.dominio.taxonomia import MOTIVOS

# conversation_id: (motivos em ordem, recontato, tom)
R = {
"CV915515":("rastreio_status",0,"neutro"), "CV912030":("cupom_promocao_nao_aplicou",0,"neutro"),
"CV914810":("item_faltante",0,"irritado"), "CV913277":("sem_conteudo",0,"neutro"),
"CV911650":("atraso",0,"irritado"), "CV913721":("rastreio_status",1,"irritado"),
"CV920868":("arrependimento",0,"neutro"), "CV919487":("arrependimento",0,"neutro"),
"CV920357":("reacao_adversa",0,"neutro"), "CV911940":("reacao_adversa",0,"neutro"),
"CV919410":("brinde_faltante",1,"irritado"), "CV918276":("atraso",1,"urgente"),
"CV921299":("alteracao_endereco;elogio",0,"neutro"), "CV919310":("reacao_adversa",0,"urgente"),
"CV912730":("atraso;item_faltante",0,"urgente"), "CV911055":("duvida_produto;cupom_promocao_nao_aplicou",0,"neutro"),
"CV918838":("compra_duplicada_cliente",0,"neutro"), "CV920956":("duvida_produto;arrependimento",0,"neutro"),
"CV914956":("brinde_faltante",0,"neutro"), "CV919922":("pagamento_nao_confirmado;atraso",0,"urgente"),
"CV921766":("cancelar_recomprar_cupom",0,"neutro"), "CV921268":("troca_fragrancia",0,"neutro"),
"CV921988":("cobranca_duplicada",0,"neutro"), "CV913067":("atraso",0,"irritado"),
"CV918153":("insatisfacao_produto",0,"neutro"), "CV911232":("duvida_saude",0,"neutro"),
"CV918462":("arrependimento",0,"neutro"), "CV917349":("duvida_saude",0,"neutro"),
"CV913614":("duvida_produto",0,"neutro"), "CV913744":("insatisfacao_produto",0,"neutro"),
"CV914299":("pagamento_nao_confirmado;cupom_promocao_nao_aplicou",0,"neutro"), "CV918751":("brinde_faltante",1,"irritado"),
"CV919912":("brinde_faltante",0,"neutro"), "CV921164":("duvida_saude;atraso",0,"irritado"),
"CV921480":("duvida_produto",0,"neutro"), "CV913530":("elogio",0,"neutro"),
"CV921057":("avaria_vazamento",0,"neutro"), "CV911196":("cobranca_duplicada",1,"neutro"),
"CV918861":("duvida_produto",0,"neutro"), "CV913131":("avaria_vazamento",0,"neutro"),
"CV913388":("duvida_saude",0,"neutro"), "CV918520":("arrependimento;item_faltante",0,"neutro"),
"CV914988":("rastreio_status;duvida_produto",1,"irritado"), "CV910641":("cobranca_duplicada;insatisfacao_produto",0,"neutro"),
"CV914877":("rastreio_status",1,"neutro"), "CV920584":("arrependimento;rastreio_status",0,"neutro"),
"CV911895":("arrependimento",0,"neutro"), "CV916061":("cupom_promocao_nao_aplicou;cobranca_duplicada",0,"neutro"),
"CV913451":("troca_outros;atraso",0,"irritado"), "CV920229":("duvida_saude;rastreio_status",0,"neutro"),
"CV916596":("cobranca_duplicada",0,"neutro"), "CV910212":("rastreio_status",0,"neutro"),
"CV912455":("duvida_saude",0,"neutro"), "CV913368":("cupom_promocao_nao_aplicou",0,"neutro"),
"CV911720":("reacao_adversa",0,"neutro"), "CV918433":("cobranca_nao_reconhecida",0,"neutro"),
"CV910909":("avaria_vazamento",0,"neutro"), "CV910375":("troca_outros",0,"neutro"),
"CV919408":("item_faltante",0,"neutro"), "CV910627":("sem_conteudo",0,"neutro"),
"CV918783":("alteracao_endereco",0,"neutro"), "CV918667":("insatisfacao_produto",0,"neutro"),
"CV916917":("avaria_vazamento",0,"irritado"), "CV919235":("reacao_adversa",0,"neutro"),
"CV910863":("duvida_produto",0,"neutro"), "CV918645":("cobranca_nao_reconhecida",0,"neutro"),
"CV919895":("pagamento_nao_confirmado",0,"neutro"), "CV913636":("atraso",1,"urgente"),
"CV919156":("cupom_promocao_nao_aplicou",0,"neutro"), "CV911115":("arrependimento",0,"neutro"),
"CV916746":("alteracao_endereco",0,"neutro"), "CV911204":("duvida_produto",0,"neutro"),
"CV921223":("rastreio_status",0,"neutro"), "CV921940":("alteracao_endereco",0,"neutro"),
"CV919674":("atraso",0,"irritado"), "CV920276":("troca_outros",0,"neutro"),
"CV912070":("duvida_produto",0,"neutro"), "CV919484":("cobranca_duplicada",0,"neutro"),
"CV915381":("rastreio_status",0,"neutro"), "CV920006":("avaria_vazamento",0,"neutro"),
"CV917844":("avaria_vazamento",0,"neutro"), "CV917032":("reacao_adversa",0,"neutro"),
"CV915931":("avaria_vazamento",1,"irritado"), "CV919283":("rastreio_status;duvida_produto",0,"irritado"),
"CV917050":("duvida_saude;avaria_vazamento",0,"irritado"), "CV913255":("troca_outros;cobranca_duplicada",0,"neutro"),
"CV921322":("insatisfacao_produto",0,"neutro"), "CV911457":("cancelar_recomprar_cupom;cobranca_duplicada",0,"neutro"),
"CV916939":("insatisfacao_produto",0,"neutro"), "CV915328":("rastreio_status",0,"neutro"),
"CV910311":("item_faltante;arrependimento;brinde_faltante",1,"irritado"), "CV918385":("pagamento_nao_confirmado",0,"neutro"),
"CV912782":("item_faltante",0,"irritado"), "CV921866":("insatisfacao_produto;cobranca_duplicada",0,"neutro"),
"CV914554":("reacao_adversa",0,"neutro"), "CV916811":("insatisfacao_produto",0,"neutro"),
}

if __name__ == "__main__":
    arq = Path(__file__).resolve().parents[1] / "dados" / "gabarito.csv"
    g = pd.read_csv(arq)
    assert set(g.conversation_id) == set(R), "ids divergentes"
    for mot, *_ in R.values():
        assert all(m in MOTIVOS for m in mot.split(";")), mot
    g["motivos"] = g.conversation_id.map(lambda c: R[c][0])
    g["motivo_principal"] = g.motivos.str.split(";").apply(motivo_principal)
    g["recontato"] = g.conversation_id.map(lambda c: bool(R[c][1]))
    g["tom"] = g.conversation_id.map(lambda c: R[c][2])
    g["revisado"] = False
    g.to_csv(arq, index=False)
    print("ok", len(g))
