"""Avalia o classificador LLM contra o gabarito e compara com a tag manual.

Uso: python -m scripts.avaliar_classificacao [modelo]
"""
import sys
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from atendimento.servicos.classificacao import MODELO_PADRAO, classificar_lote

load_dotenv()
RAIZ = Path(__file__).resolve().parents[1]

# Tag manual → motivos que ela pode representar
TAG_PARA_MOTIVOS = {
    "Rastreio": {"rastreio_status"}, "Atraso": {"atraso"},
    "Produto faltando": {"item_faltante", "brinde_faltante"},
    "Avaria": {"avaria_vazamento", "erro_personalizacao"},
    "Troca": {"troca_fragrancia", "troca_outros"},
    "Cancelamento": {"arrependimento", "compra_duplicada_cliente", "cancelar_recomprar_cupom"},
    "Reclamação produto": {"insatisfacao_produto"},
    "Financeiro": {"cobranca_duplicada", "cobranca_nao_reconhecida", "pagamento_nao_confirmado", "cashback"},
    "Dúvida": {"duvida_produto", "duvida_saude"},
    "Promoção": {"cupom_promocao_nao_aplicou", "frete_gratis"},
    "Endereço": {"alteracao_endereco"}, "Elogio": {"elogio"}, "Outros": {"outro"},
}
SAUDE = {"reacao_adversa", "duvida_saude"}


def main(modelo: str) -> None:
    gab = pd.read_csv(RAIZ / "dados" / "gabarito.csv")
    msgs = pd.read_csv(RAIZ / "case_atendimento" / "mensagens.csv").sort_values("timestamp")
    cli = msgs[msgs.autor == "cliente"].groupby("conversation_id").texto.apply(list)
    entradas = [cli.get(c, []) for c in gab.conversation_id]

    t0 = time.time()
    res = classificar_lote(entradas, modelo=modelo)
    print(f"{modelo}: {len(res)} conversas em {time.time() - t0:.0f}s")

    erros = [(c, r) for c, r in zip(gab.conversation_id, res) if isinstance(r, Exception)]
    for c, e in erros:
        print("ERRO", c, type(e).__name__, str(e)[:200])
    ok = [(i, r) for i, r in enumerate(res) if not isinstance(r, Exception)]
    g = gab.iloc[[i for i, _ in ok]].copy()
    g["pred_motivos"] = [";".join(m.motivo for m in r.motivos) or "sem_conteudo" for _, r in ok]
    g["pred_principal"] = [r.motivo_principal for _, r in ok]
    g["pred_recontato"] = [r.recontato for _, r in ok]
    g["pred_tom"] = [r.tom for _, r in ok]
    g["pred_confianca"] = [r.confianca for _, r in ok]

    real = g.motivos.str.split(";").apply(set)
    pred = g.pred_motivos.str.split(";").apply(set)
    tp = sum(len(a & b) for a, b in zip(real, pred))
    precisao, recall = tp / sum(map(len, pred)), tp / sum(map(len, real))
    saude_real = real.apply(lambda s: bool(s & SAUDE))
    saude_pred = pred.apply(lambda s: bool(s & SAUDE))

    t = g[g.tag_agente.notna()]
    tag_ok = t.apply(lambda r: r.motivo_principal in TAG_PARA_MOTIVOS[r.tag_agente], axis=1)

    print(f"\nMotivo principal  — LLM: {(g.pred_principal == g.motivo_principal).mean():.1%} | tag manual: {tag_ok.mean():.1%}")
    print(f"Conjunto exato de motivos: {(real == pred).mean():.1%}")
    print(f"Motivos (multi-label) precisão {precisao:.1%} | recall {recall:.1%}")
    print(f"Saúde: recall {(saude_pred & saude_real).sum()}/{saude_real.sum()} | falsos positivos {(saude_pred & ~saude_real).sum()}")
    print(f"Recontato: {(g.pred_recontato == g.recontato).mean():.1%} | Tom: {(g.pred_tom == g.tom).mean():.1%}")

    div = g[real != pred]
    print(f"\nDivergências ({len(div)}):")
    for _, r in div.iterrows():
        print(f"  {r.conversation_id} gabarito={r.motivos} | llm={r.pred_motivos} ({r.pred_confianca})")
    g.to_csv(RAIZ / "dados" / f"predicoes_{modelo.replace('/', '_')}.csv", index=False)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else MODELO_PADRAO)
