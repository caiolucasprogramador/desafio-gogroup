"""Roda o grafo em conversas reais e imprime a trilha. Também gera docs/grafo.md (diagrama).

Uso: python -m scripts.rodar_grafo CV919235 CV912030 ...
"""
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[1]
load_dotenv(RAIZ / ".env")

from atendimento.grafo.fluxo import grafo  # noqa: E402

(RAIZ / "docs" / "grafo.md").write_text(
    "# Fluxo do agente de atendimento\n\n```mermaid\n" + grafo.get_graph().draw_mermaid() + "```\n", encoding="utf-8")

conv = pd.read_csv(RAIZ / "case_atendimento" / "conversas.csv").set_index("conversation_id")
msgs = pd.read_csv(RAIZ / "case_atendimento" / "mensagens.csv").sort_values("timestamp")

for cid in sys.argv[1:]:
    c = conv.loc[cid]
    estado = grafo.invoke({
        "conversation_id": cid, "customer_id": c.customer_id, "order_id": c.order_id, "canal": c.canal,
        "marca": c.marca, "data_abertura": c.data_abertura, "status_conversa": c.status,
        "mensagens_cliente": msgs[(msgs.conversation_id == cid) & (msgs.autor == "cliente")].texto.tolist(),
        "trilha": [],
    })
    print(f"\n=== {cid} ({c.canal}) ===")
    for linha in estado["trilha"]:
        print("  ·", linha)
    if acao := estado.get("acao"):
        print(f"  → AÇÃO: {acao.tipo} [{acao.destino}]")
