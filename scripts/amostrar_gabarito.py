"""Gera amostra estratificada de ~100 conversas para o gabarito rotulado à mão.

Estratos: tag manual do agente (inclusive sem tag) + casos raros que importam
(saúde, cobrança duplicada, múltiplas intenções), para que o gabarito
não seja dominado por rastreio.
"""
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "case_atendimento"
SAIDA = RAIZ / "dados"
SEED = 42

conv = pd.read_csv(DADOS / "conversas.csv")
msgs = pd.read_csv(DADOS / "mensagens.csv").sort_values(["conversation_id", "timestamp"])

texto_cliente = msgs[msgs.autor == "cliente"].groupby("conversation_id").texto.apply(" | ".join)
conv = conv.join(texto_cliente.rename("texto_cliente"), on="conversation_id")
com_texto = conv[conv.texto_cliente.notna()]

def contem(padrao: str) -> pd.Series:
    return com_texto.texto_cliente.str.contains(padrao, case=False, regex=True)

forcados = {
    "saude": contem(r"alergi|coceir|irrit|queim|inchad|descam|gravidez|grávida|amament|criança|bebê"),
    "cobranca_dupla": contem(r"duas vezes|cobrad. de novo|saiu duas"),
    "multi_intencao": contem(r"E outra coisa:"),
}
amostra = [com_texto[m].sample(min(n, m.sum()), random_state=SEED)
           for m, n in zip(forcados.values(), (12, 6, 12))]
ja = pd.concat(amostra).conversation_id

# 5 por tag manual (inclui NaN = sem tag), fora os já escolhidos
resto = com_texto[~com_texto.conversation_id.isin(ja)].copy()
resto["estrato"] = resto.tag_agente.fillna("SEM_TAG")
amostra.append(resto.groupby("estrato", group_keys=False).apply(
    lambda g: g.sample(min(5, len(g)), random_state=SEED)))
# 2 abandonos no bot, para conferir a regra sem_conteudo
amostra.append(conv[conv.texto_cliente.isna()].sample(2, random_state=SEED))

gab = pd.concat(amostra).drop_duplicates("conversation_id").sample(frac=1, random_state=SEED)
ids = list(gab.conversation_id)

# Arquivo de leitura: transcrição completa
linhas = []
for i, cid in enumerate(ids, 1):
    c = gab.set_index("conversation_id").loc[cid]
    linhas.append(f"## {i}. {cid} | {c.canal} | {c.marca} | tag_agente={c.tag_agente} | status={c.status}")
    for _, m in msgs[msgs.conversation_id == cid].iterrows():
        linhas.append(f"- **{m.autor}**: {m.texto}")
    linhas.append("")
(SAIDA / "gabarito_leitura.md").write_text("\n".join(linhas), encoding="utf-8")

gab[["conversation_id", "canal", "tag_agente"]].assign(
    motivos="", motivo_principal="", recontato="", tom="", revisado=""
).to_csv(SAIDA / "gabarito.csv", index=False)
print(f"{len(gab)} conversas | por tag manual:", gab.tag_agente.fillna("SEM_TAG").value_counts().to_dict())
