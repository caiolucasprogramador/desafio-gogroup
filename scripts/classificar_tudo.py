"""Classifica as conversas históricas em lote (com cache retomável).

Uso:
  python -m scripts.classificar_tudo --gabarito   # só as conversas do gabarito (validar o modo lote)
  python -m scripts.classificar_tudo              # todas as 4.000
  --modelo=gemini-2.5-flash-lite                  # escolhe o modelo (padrão: MODELO_PADRAO)
"""
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from atendimento.lote import ClassificadorLote, normalizar
from atendimento.servicos.classificacao import MODELO_PADRAO

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
RAIZ = Path(__file__).resolve().parents[1]

conv = pd.read_csv(RAIZ / "case_atendimento" / "conversas.csv")
msgs = pd.read_csv(RAIZ / "case_atendimento" / "mensagens.csv").sort_values("timestamp")
cli = msgs[msgs.autor == "cliente"].groupby("conversation_id").texto.apply(list)
if "--gabarito" in sys.argv:
    conv = conv[conv.conversation_id.isin(pd.read_csv(RAIZ / "dados" / "gabarito.csv").conversation_id)]

entradas = {c: cli.get(c, []) for c in conv.conversation_id}
modelo = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--modelo=")), MODELO_PADRAO)
clf = ClassificadorLote(RAIZ / "dados" / "cache_classificacao.jsonl", modelo=modelo)
clf.classificar_unicos([normalizar(m) for m in entradas.values() if m])

linhas = []
for cid, m in entradas.items():
    r = clf.resultado(m)
    if r is None:
        continue
    linhas.append({"conversation_id": cid, "motivos": ";".join(x.motivo for x in r.motivos) or "sem_conteudo",
                   "motivo_principal": r.motivo_principal, "categoria_principal": r.categoria_principal,
                   "recontato": r.recontato, "tom": r.tom, "confianca": r.confianca, "origem": r.origem,
                   "evidencias": " | ".join(x.evidencia for x in r.motivos)})
sufixo = modelo.replace("/", "_")
saida = RAIZ / "dados" / (f"classificacoes_gabarito_{sufixo}.csv" if "--gabarito" in sys.argv else f"classificacoes_{sufixo}.csv")
pd.DataFrame(linhas).to_csv(saida, index=False)
print(f"{len(linhas)}/{len(entradas)} conversas classificadas → {saida.name}")
