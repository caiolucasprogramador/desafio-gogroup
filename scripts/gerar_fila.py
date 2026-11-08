"""Gera a fila priorizada (pendentes + reabertas) com enriquecer + priorizar + elegibilidade, sem LLM (classificação do cache).

Uso: python -m scripts.gerar_fila [--modelo=gemini-3.5-flash-lite]
"""
import sys
from pathlib import Path

import pandas as pd

from atendimento.lote import ClassificadorLote
from atendimento.servicos import dados
from atendimento.servicos.decisao import decidir, regra_fixa
from atendimento.servicos.elegibilidade import avaliar, resumir
from atendimento.servicos.enriquecimento import enriquecer
from atendimento.servicos.priorizacao import explicar, priorizar

RAIZ = Path(__file__).resolve().parents[1]
modelo = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--modelo=")), "gemini-3.5-flash-lite")

clf = ClassificadorLote(RAIZ / "dados" / "cache_classificacao.jsonl", modelo=modelo)
msgs = dados.mensagens()
cli = msgs[msgs.autor == "cliente"].groupby("conversation_id").texto.apply(list)
fila = dados.conversas()
fila = fila[fila.status.isin(["pendente", "reaberto"])]

linhas = []
for c in fila.itertuples():
    classif = clf.resultado(cli.get(c.conversation_id, []))
    if classif is None:
        print("sem classificação no cache:", c.conversation_id)
        continue
    ctx, classif = enriquecer(c.conversation_id, c.customer_id, c.order_id, str(c.data_abertura), classif)
    p = priorizar(classif, ctx, c.canal, c.status)
    eleg = avaliar(classif, ctx, c.marca, cli.get(c.conversation_id, []))
    dec = regra_fixa(classif, c.canal) or decidir(classif, ctx, eleg)
    linhas.append({
        "conversation_id": c.conversation_id, "canal": c.canal, "marca": c.marca, "status": c.status,
        "motivos": ";".join(m.motivo for m in classif.motivos) or "sem_conteudo",
        "motivo_principal": classif.motivo_principal, "topo_da_fila": p.topo_da_fila, "score": p.score,
        **{f"f_{k}": v for k, v in p.fatores.items()},
        "valor": ctx.valor, "status_entrega": ctx.status_entrega, "aguardando_resposta": ctx.aguardando_resposta,
        "horas_aguardando": ctx.horas_aguardando, "correcoes": "; ".join(ctx.correcoes), "explicacao": explicar(p),
        "elegibilidade_principal": eleg.resultado, "elegibilidade": resumir(eleg),
        "modo": dec.modo, "fila_destino": dec.fila_destino, "acao_principal": dec.acao_proposta,
        "acoes": "; ".join(f"{a.motivo}→{a.tipo}" for a in dec.acoes) or dec.acao_proposta,
    })

df = pd.DataFrame(linhas).sort_values(["topo_da_fila", "score"], ascending=False)
df.insert(0, "posicao", range(1, len(df) + 1))
df.to_csv(RAIZ / "dados" / "fila_priorizada.csv", index=False)

print(f"Fila: {len(df)} conversas | topo (saúde): {df.topo_da_fila.sum()} | correções factuais: {(df.correcoes != '').sum()}")
print(f"Score: {df.score.describe(percentiles=[.25, .5, .75, .9]).round(1).to_dict()}")
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 90)
for titulo, parte in [("Topo (saúde)", df[df.topo_da_fila].head(5)), ("Primeiros fora de saúde", df[~df.topo_da_fila].head(10)),
                      ("Últimos da fila", df.tail(5))]:
    print(f"\n{titulo}:")
    print(parte[["posicao", "conversation_id", "canal", "motivos", "explicacao"]].to_string(index=False))
