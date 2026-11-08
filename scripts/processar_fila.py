"""Processa a fila (pendentes + reabertas) pelo GRAFO completo e grava dados/resultados_grafo.jsonl.

É o insumo da API e do painel. Sem LLM: classificação do cache, resto determinístico.
Uso: python -m scripts.processar_fila
"""
import json
import os
import time
from collections import Counter
from pathlib import Path

os.environ.setdefault("SEM_LLM", "1")

from atendimento.grafo.fluxo import grafo  # noqa: E402
from atendimento.servicos import dados  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "dados" / "resultados_grafo.jsonl"


def resumo(estado: dict) -> dict:
    c, p, d, a = (estado.get(k) for k in ("classificacao", "prioridade", "decisao", "acao"))
    return {
        "conversation_id": estado["conversation_id"], "canal": estado["canal"], "marca": estado["marca"],
        "status_conversa": estado.get("status_conversa"),
        "motivos": [m.motivo for m in c.motivos] if c else [],
        "motivo_principal": c.motivo_principal if c else None,
        "categoria_principal": c.categoria_principal if c else None,
        "score": p.score if p else None, "topo_da_fila": p.topo_da_fila if p else False,
        "modo": d.modo if d else "encerrado", "fila_destino": d.fila_destino if d else None,
        "acoes": [x.model_dump() for x in d.acoes] if d else [],
        "rascunho_resposta": a.rascunho_resposta if a else None,
        "destino": a.destino if a else "nenhum",
        "elegibilidade": [x.model_dump() for x in estado["elegibilidade"].avaliacoes] if estado.get("elegibilidade") else [],
        "contexto": estado["contexto"].model_dump() if estado.get("contexto") else None,
        "trilha": estado["trilha"],
    }


if __name__ == "__main__":
    conv = dados.conversas()
    ids = conv[conv.status.isin(["pendente", "reaberto"])].conversation_id.tolist()
    t0, resultados = time.time(), []
    for i, cid in enumerate(ids, 1):
        resultados.append(resumo(grafo.invoke(dados.entrada_do_grafo(cid))))
        if i % 200 == 0:
            print(f"  {i}/{len(ids)}")
    resultados.sort(key=lambda r: (not r["topo_da_fila"], -(r["score"] or 0)))
    with SAIDA.open("w", encoding="utf-8") as f:
        for pos, r in enumerate(resultados, 1):
            f.write(json.dumps({"posicao": pos, **r}, ensure_ascii=False, default=str) + "\n")

    modos = Counter(r["modo"] for r in resultados)
    print(f"{len(resultados)} conversas em {time.time() - t0:.0f}s → {SAIDA.name}")
    print("Modo:", dict(modos), f"| automático: {modos['automatico'] / len(resultados):.0%}")
    print("Filas humanas:", dict(Counter(r["fila_destino"] for r in resultados if r["modo"] == "humano")))
    print("Com rascunho:", sum(bool(r["rascunho_resposta"]) for r in resultados))
