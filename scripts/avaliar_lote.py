"""Compara o CSV de classificações em lote com o gabarito. Uso: python -m scripts.avaliar_lote <arquivo.csv>"""
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
SAUDE = {"reacao_adversa", "duvida_saude"}

g = pd.read_csv(RAIZ / "dados" / "gabarito.csv").merge(pd.read_csv(sys.argv[1]), on="conversation_id", suffixes=("", "_p"))
real, pred = g.motivos.str.split(";").apply(set), g.motivos_p.str.split(";").apply(set)
tp = sum(len(a & b) for a, b in zip(real, pred))
sr, sp = real.apply(lambda s: bool(s & SAUDE)), pred.apply(lambda s: bool(s & SAUDE))
print(f"n={len(g)} | principal {(g.motivo_principal == g.motivo_principal_p).mean():.1%} | conjunto exato {(real == pred).mean():.1%}"
      f" | precisão {tp / sum(map(len, pred)):.1%} recall {tp / sum(map(len, real)):.1%}")
print(f"saúde {(sr & sp).sum()}/{sr.sum()} FP {(sp & ~sr).sum()} | recontato {(g.recontato == g.recontato_p).mean():.1%} | tom {(g.tom == g.tom_p).mean():.1%}")
for _, r in g[real != pred].iterrows():
    print(f"  {r.conversation_id} {r.motivos} → {r.motivos_p}")
