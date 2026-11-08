"""Roda o grafo em conversas reais e imprime a trilha e o rascunho. Também gera docs/grafo.md (diagrama).

Uso: SEM_LLM=1 python -m scripts.rodar_grafo CV919235 CV912030 ...
"""
import sys
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[1]
load_dotenv(RAIZ / ".env")

from atendimento.grafo.fluxo import grafo  # noqa: E402
from atendimento.servicos.dados import entrada_do_grafo  # noqa: E402

(RAIZ / "docs" / "grafo.md").write_text(
    "# Fluxo do agente de atendimento\n\n```mermaid\n" + grafo.get_graph().draw_mermaid() + "```\n", encoding="utf-8")

for cid in sys.argv[1:]:
    entrada = entrada_do_grafo(cid)
    estado = grafo.invoke(entrada)
    print(f"\n=== {cid} ({entrada['canal']}) ===")
    for linha in estado["trilha"]:
        print("  ·", linha)
    if acao := estado.get("acao"):
        print(f"  → AÇÃO: {acao.tipo} [{acao.destino}]")
        if acao.rascunho_resposta:
            print("  → RASCUNHO:\n    " + acao.rascunho_resposta.replace("\n", "\n    "))
