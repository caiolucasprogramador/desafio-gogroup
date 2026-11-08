"""Compara rascunho de template x reescrita do LLM numa amostra estratificada por tipo de ação.

Uso: python -m scripts.amostra_redacao [n_por_tipo]   (padrão 3) → dados/amostra_redacao.jsonl
Usa a fila já processada (dados/resultados_grafo.jsonl) para escolher os casos.
"""
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[1]
load_dotenv(RAIZ / ".env")
os.environ["REDACAO_LLM"] = "1"
os.environ.pop("SEM_LLM", None)

from atendimento.grafo.fluxo import grafo  # noqa: E402
from atendimento.servicos.dados import entrada_do_grafo  # noqa: E402

n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
fila = [json.loads(l) for l in (RAIZ / "dados" / "resultados_grafo.jsonl").read_text(encoding="utf-8").splitlines()]
por_tipo = defaultdict(list)
for r in fila:
    if r["modo"] == "automatico":
        chave = "+".join(sorted({a["tipo"] for a in r["acoes"]}))
        por_tipo[chave if len(r["acoes"]) == 1 else "multi_motivo"].append(r["conversation_id"])
amostra = [cid for ids in por_tipo.values() for cid in ids[:n]]
print(f"{len(amostra)} conversas, tipos: {sorted(por_tipo)}")

saida, t0 = [], time.time()
for i, cid in enumerate(amostra, 1):
    entrada = entrada_do_grafo(cid)
    estado = grafo.invoke(entrada)
    a = estado["acao"]
    from atendimento.servicos.respostas import redigir
    saida.append({"conversation_id": cid, "tipos": [x.tipo for x in estado["decisao"].acoes],
                  "mensagens_cliente": estado["mensagens_cliente"],
                  "template": redigir(estado["decisao"], entrada["marca"]),
                  "final": a.rascunho_resposta, "origem": a.payload["origem_rascunho"]})
    print(f"  {i}/{len(amostra)} {cid} → {a.payload['origem_rascunho'][:90]}")
(RAIZ / "dados" / "amostra_redacao.jsonl").write_text(
    "\n".join(json.dumps(s, ensure_ascii=False) for s in saida), encoding="utf-8")
aceitos = sum(s["origem"] == "llm" for s in saida)
print(f"\nLLM aceito em {aceitos}/{len(saida)} ({aceitos / len(saida):.0%}) | {time.time() - t0:.0f}s")
