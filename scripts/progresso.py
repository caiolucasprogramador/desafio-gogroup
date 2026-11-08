"""Painel de terminal: progresso da classificação e tokens gastos por modelo/etapa.

Uso: python -m scripts.progresso [--modelo=gemini-3.5-flash-lite]
"""
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd

from atendimento.lote import VERSAO_PROMPT, normalizar

RAIZ = Path(__file__).resolve().parents[1]
modelo = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--modelo=")), "gemini-3.5-flash-lite")

msgs = pd.read_csv(RAIZ / "case_atendimento" / "mensagens.csv").sort_values("timestamp")
cli = msgs[msgs.autor == "cliente"].groupby("conversation_id").texto.apply(list)
necessarios = {normalizar(m) for m in cli}

feitos: Counter = Counter()
cache = RAIZ / "dados" / "cache_classificacao.jsonl"
chaves_modelo: set[str] = set()
if cache.exists():
    for linha in cache.read_text(encoding="utf-8").splitlines():
        r = json.loads(linha)
        if r["versao"] == VERSAO_PROMPT:
            feitos[r["modelo"]] += 1
            if r["modelo"] == modelo:
                chaves_modelo.add(r["chave"])

ok = len(necessarios & chaves_modelo)
barra = "█" * int(30 * ok / len(necessarios))
print(f"Classificação ({modelo}): {ok}/{len(necessarios)} textos únicos  [{barra:<30}] {ok / len(necessarios):.0%}")
print("Cache por modelo:", dict(feitos))

uso = RAIZ / "dados" / "uso_llm.jsonl"
if uso.exists():
    df = pd.DataFrame([json.loads(l) for l in uso.read_text(encoding="utf-8").splitlines()])
    df["dia"] = pd.to_datetime(df.quando).dt.date
    resumo = df.groupby(["dia", "modelo", "etapa"]).agg(chamadas=("total", "size"), entrada=("entrada", "sum"),
                                                         saida=("saida", "sum"), total=("total", "sum"))
    print("\nTokens por dia / modelo / etapa:")
    print(resumo.to_string())
    hoje = df[df.dia == date.today()].groupby("modelo").total.sum()
    print("\nHoje:", {m: f"{t:,}".replace(",", ".") for m, t in hoje.items()})
else:
    print("\n(sem registro de uso ainda — dados/uso_llm.jsonl é criado na primeira chamada medida)")
