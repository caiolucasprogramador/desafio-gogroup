"""Gera public/diagnostico.json: as respostas às 4 perguntas do enunciado, SÓ com agregados.

Entradas (locais, fora do git):
    case_atendimento/conversas.csv, case_atendimento/mensagens.csv
    dados/classificacoes_<modelo>.csv            classificação das 4.000 conversas (scripts.classificar_tudo)
    dados/gabarito.csv + classificacoes_gabarito_<modelo>.csv   avaliação no gabarito
    dados/resultados_grafo.jsonl                 grafo na fila pendente/reaberta (scripts.processar_fila)
    dados/resultados_grafo_historico.jsonl       grafo nas 4.000 do trimestre (scripts.processar_fila --todas)
Saída (versionada e publicada): public/diagnostico.json, no contrato de docs/plano-paralelo.md.

Uso: python -m scripts.gerar_diagnostico [--origem=/checkout/com/os/dados] [--modelo=gemini-3.5-flash-lite]
     --origem: pasta que contém case_atendimento/ e dados/ (padrão: a raiz deste repositório).
     A saída vai sempre para o public/ DESTE repositório.

Convenções do JSON:
- Contagens de conversas são da AMOSTRA (4.000 conversas, 1 em cada 3 clientes);
  totais.conversas_estimadas = amostra × FATOR_EXPANSAO (a operação inteira no trimestre).
- Custos são TRIMESTRAIS da operação inteira: custo da amostra × FATOR_EXPANSAO.
- Percentuais são frações de 0 a 1 (não dependem da expansão).
- Custo de uma conversa vai inteiro para o seu motivo principal (assim os custos somam o total).
"""
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd

from atendimento.dominio.parametros import CUSTO_CONVERSA
from atendimento.dominio.rotulos import ACOES, CANAIS, CATEGORIAS, FILAS, MOTIVOS_ROTULO
from atendimento.dominio.taxonomia import GRAVIDADE, MOTIVO_PARA_CATEGORIA, SEMPRE_HUMANO
from atendimento.servicos.anonimizacao import PADROES

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "public" / "diagnostico.json"

# parametros.md: "os arquivos trazem uma amostra aleatória de 1 em cada 3 clientes".
FATOR_EXPANSAO = 3

# --- Privacidade ------------------------------------------------------------------------
# IDs do case: conversa CV…, cliente CL…, pedido GB…/GC…, mensagem M…
PADROES_ID = [re.compile(p) for p in (r"\bCV\d+", r"\bCL\d+", r"\bG[A-Z]\d+", r"\bM\d{5,}")]


def problemas_de_privacidade(texto_json: str, mensagens: list[str] | None = None) -> list[str]:
    """Lista o que impede publicar o JSON (vazia = pode publicar).

    Sempre: IDs do case e dados pessoais (mesmos padrões do nó `anonimizar`).
    Com `mensagens`: qualquer sequência de 6 palavras copiada de uma mensagem.
    """
    problemas = [f"ID do case: {m.group()}" for p in PADROES_ID for m in p.finditer(texto_json)]
    problemas += [f"dado pessoal ({marcador})" for marcador, p in PADROES if p.search(texto_json)]
    if mensagens:
        problemas += [f"trecho de mensagem: “{t}”" for t in _trechos_copiados(texto_json, mensagens)]
    return problemas


def _ngramas(texto: str, n: int = 6) -> set[str]:
    palavras = re.findall(r"\w+", texto.lower())
    return {" ".join(palavras[i:i + n]) for i in range(len(palavras) - n + 1)}


def _trechos_copiados(texto_json: str, mensagens: list[str]) -> set[str]:
    textos = [v for v in _strings(json.loads(texto_json))]
    nossos = set().union(*map(_ngramas, textos)) if textos else set()
    return nossos & set().union(*map(_ngramas, mensagens))


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v)


# --- Formatação -------------------------------------------------------------------------

def reais(valor_amostra: float) -> int:
    """Custo da amostra → custo trimestral da operação, em reais inteiros."""
    return round(valor_amostra * FATOR_EXPANSAO)


def frac(parte: float, todo: float) -> float:
    return round(parte / todo, 4) if todo else 0.0


def brl(v: float) -> str:
    return "R$ " + f"{v:,.0f}".replace(",", ".")


def pct(x: float, casas: int = 0) -> str:
    """0.016 → "1,6%" (vírgula decimal, como a página exibe)."""
    return f"{x:.{casas}%}".replace(".", ",")


# --- Carga ------------------------------------------------------------------------------

def carregar_conversas(origem: Path, modelo: str) -> pd.DataFrame:
    """Uma linha por conversa do histórico, com a classificação e o custo do canal (amostra)."""
    conv = pd.read_csv(origem / "case_atendimento" / "conversas.csv", parse_dates=["data_abertura"])
    clf = pd.read_csv(origem / "dados" / f"classificacoes_{modelo.replace('/', '_')}.csv")
    d = conv.merge(clf[["conversation_id", "motivos", "motivo_principal", "categoria_principal", "recontato"]],
                   on="conversation_id", how="left", validate="one_to_one")
    if (falta := d.motivo_principal.isna().sum()):
        raise SystemExit(f"{falta} conversas sem classificação: rode scripts.classificar_tudo antes.")
    d["custo"] = d.canal.map(CUSTO_CONVERSA)
    d["recontato"] = d.recontato.astype(str).str.lower().eq("true")
    return d


def carregar_resultados(origem: Path, arquivo: str = "resultados_grafo.jsonl") -> list[dict]:
    caminho = origem / "dados" / arquivo
    return [json.loads(linha) for linha in caminho.read_text(encoding="utf-8").splitlines()]


# --- Blocos do JSON ---------------------------------------------------------------------

def bloco_classificacao(origem: Path, modelo: str) -> dict:
    """Mesma conta de scripts.avaliar_classificacao, mas lendo as predições já gravadas (sem LLM)."""
    from scripts.avaliar_classificacao import SAUDE, TAG_PARA_MOTIVOS

    gab = pd.read_csv(origem / "dados" / "gabarito.csv")
    pred = pd.read_csv(origem / "dados" / f"classificacoes_gabarito_{modelo.replace('/', '_')}.csv")
    g = gab.merge(pred[["conversation_id", "motivos", "motivo_principal"]], on="conversation_id",
                  suffixes=("", "_pred"), validate="one_to_one")
    real = g.motivos.fillna("sem_conteudo").str.split(";").apply(set)
    prev = g.motivos_pred.fillna("sem_conteudo").str.split(";").apply(set)
    acertos = sum(len(a & b) for a, b in zip(real, prev))
    saude_real = real.apply(lambda s: bool(s & SAUDE))
    saude_ok = (saude_real & prev.apply(lambda s: bool(s & SAUDE))).sum()
    t = g[g.tag_agente.notna()]
    tag_ok = t.apply(lambda r: r.motivo_principal in TAG_PARA_MOTIVOS[r.tag_agente], axis=1)
    return {
        "amostra_gabarito": len(g),
        "acerto_agente": frac((g.motivo_principal_pred == g.motivo_principal).sum(), len(g)),
        "acerto_tag_manual": frac(tag_ok.sum(), len(t)),
        "recall_motivos": frac(acertos, sum(map(len, real))),
        "saude_detectada": f"{saude_ok}/{saude_real.sum()}",
        "modelo": modelo,
        "observacao": "Gabarito rotulado por IA, sem validação humana. Contagens de conversas são da amostra "
                      f"(1 em cada {FATOR_EXPANSAO} clientes); custos são trimestrais, estimados para a "
                      f"operação inteira (amostra × {FATOR_EXPANSAO}).",
    }


def bloco_p1(d: pd.DataFrame) -> dict:
    n, custo_total = len(d), d.custo.sum()

    def linha(grupo: pd.DataFrame) -> dict:
        return {"conversas": len(grupo), "pct_conversas": frac(len(grupo), n),
                "custo": reais(grupo.custo.sum()), "pct_custo": frac(grupo.custo.sum(), custo_total)}

    categorias = [{"categoria": c, "rotulo": CATEGORIAS[c], **linha(g)}
                  for c, g in d.groupby("categoria_principal")]
    motivos = [{"motivo": m, "rotulo": MOTIVOS_ROTULO[m], "categoria": MOTIVO_PARA_CATEGORIA[m], **linha(g),
                "gravidade": GRAVIDADE[m]} for m, g in d.groupby("motivo_principal")]
    canais = [{"canal": c, "rotulo": CANAIS[c], "conversas": len(g), "pct_conversas": frac(len(g), n),
               "custo_unitario": CUSTO_CONVERSA[c], "custo": reais(g.custo.sum()),
               "pct_custo": frac(g.custo.sum(), custo_total)} for c, g in d.groupby("canal")]
    por_custo = lambda x: (-x["custo"], -x["conversas"])  # noqa: E731
    return {"categorias": sorted(categorias, key=por_custo), "motivos": sorted(motivos, key=por_custo),
            "canais": sorted(canais, key=por_custo)}


# Contatos que não precisariam existir. A máscara define a conversa; o texto diz como evitar.
EVITAVEIS = [
    ("recontato", "Cliente voltando a perguntar", lambda d: d.recontato,
     "Responder o primeiro contato por completo, com todos os assuntos, e avisar proativamente quando houver novidade."),
    ("rastreio", "Dúvida de rastreio", lambda d: d.motivo_principal == "rastreio_status",
     "Aviso proativo de status (WhatsApp/e-mail) e link de rastreio na confirmação do pedido."),
    ("abandono_bot", "Abandono no bot", lambda d: d.motivo_principal == "sem_conteudo",
     "Menu do bot guiado por motivo, com a resposta para os casos simples antes de abrir atendimento."),
    ("endereco", "Alteração de endereço", lambda d: d.motivo_principal == "alteracao_endereco",
     "Autoatendimento no site para alterar o endereço enquanto o pedido não foi separado."),
]


def bloco_p2(d: pd.DataFrame) -> dict:
    itens, algum = [], pd.Series(False, index=d.index)
    for id_, rotulo, mascara, como in EVITAVEIS:
        m = mascara(d)
        algum |= m
        itens.append({"id": id_, "rotulo": rotulo, "conversas": int(m.sum()), "custo": reais(d[m].custo.sum()),
                      "como_evitar": como})
    # total sem contar duas vezes a conversa que cai em mais de um item (ex.: recontato sobre rastreio)
    return {"total_custo": reais(d[algum].custo.sum()), "itens": sorted(itens, key=lambda x: -x["custo"])}


def bloco_p3(d: pd.DataFrame) -> dict:
    n, total = len(d), d.custo.sum()
    ra = d[d.canal == "reclame_aqui"]
    entrega = d[d.motivo_principal.isin(["atraso", "rastreio_status"])]
    rec = d[d.recontato]
    saude = d[d.motivos.str.split(";").apply(lambda s: bool(set(s) & SEMPRE_HUMANO))]
    vezes = CUSTO_CONVERSA["reclame_aqui"] / CUSTO_CONVERSA["whatsapp"]
    focos = [
        ("Reclame Aqui", ra, f"{pct(frac(len(ra), n))} dos contatos e {pct(frac(ra.custo.sum(), total))} do custo: "
         f"cada caso custa {vezes:.0f}× um WhatsApp e a resposta é pública."),
        ("Atraso e rastreio", entrega, f"Maior volume ({pct(frac(len(entrega), n))} dos contatos); a dúvida de "
         "rastreio some com aviso proativo e o atraso vira chamado automático na transportadora."),
        ("Recontato", rec, f"{pct(frac(len(rec), n))} das conversas são o cliente voltando a perguntar: "
         "contatos que só existem porque o primeiro não resolveu."),
        ("Saúde", saude, f"Poucos casos ({pct(frac(len(saude), n), 1)}), mas risco ao cliente e prazo de 24h de "
         "cosmetovigilância: fura a fila e vai sempre para a responsável técnica."),
    ]
    return {
        "criterio": "Custo trimestral × gravidade × facilidade de ação: primeiro o que concentra custo e tem "
                    "ação clara; saúde entra pela gravidade, não pelo custo.",
        "itens": [{"rank": i, "foco": foco, "porque": porque, "conversas": len(g), "custo": reais(g.custo.sum())}
                  for i, (foco, g, porque) in enumerate(focos, 1)],
    }


# Motivos sem política escrita que poderiam ganhar uma (saúde e suspeita de fraude ficam com humano).
SUGESTAO_POLITICA = {
    "brinde_faltante": "Política de reenvio do brinde (ou cupom equivalente) quando a promoção estava ativa.",
    "duvida_produto": "Base de conhecimento de produtos (composição, uso, validade) para o agente consultar.",
    "insatisfacao_produto": "Política de troca ou cupom por insatisfação, como a que já existe para fragrância.",
    "troca_outros": "Política geral de troca (tamanho, modelo, expectativa) com prazo e condições.",
    "pagamento_nao_confirmado": "Consulta automática da baixa do pagamento no gateway antes de responder.",
    "cupom_promocao_nao_aplicou": "Regras de cupons e promoções acessíveis ao agente, com crédito automático.",
    "cashback": "Regras de cashback e consulta de saldo acessíveis ao agente.",
    "frete_gratis": "Regra de frete grátis acessível ao agente, com estorno automático da diferença.",
}


def _acao_principal(r: dict) -> str:
    """Igual a decidir(): a ação do motivo principal (ou a primeira)."""
    return next((a for a in r["acoes"] if a["motivo"] == r["motivo_principal"]), r["acoes"][0])["tipo"]


def bloco_p4(resultados: list[dict]) -> dict:
    auto = [r for r in resultados if r["modo"] == "automatico"]
    humano = [r for r in resultados if r["modo"] == "humano"]
    acoes = Counter(_acao_principal(r) for r in auto)
    filas = Counter(r["fila_destino"] for r in humano)

    # Conversa humana cujo ÚNICO bloqueio é um motivo sem regra: viraria automática com a política.
    destravaria: Counter = Counter()
    for r in humano:
        bloqueios = {(a["motivo"], a["tipo"]) for a in r["acoes"] if a["modo"] == "humano"}
        if len(bloqueios) == 1 and (m := next(iter(bloqueios)))[1] == "encaminhar_humano" and m[0] in SUGESTAO_POLITICA:
            destravaria[m[0]] += 1

    so_pede_info = acoes["solicitar_informacoes"]
    return {
        "fila_avaliada": len(resultados),
        "automatico": len(auto),
        "humano": len(humano),
        "resolucao_completa_pct": frac(len(auto) - so_pede_info, len(resultados)),
        "por_acao": [{"acao": a, "rotulo": ACOES.get(a, a.replace("_", " ")), "modo": "automatico", "conversas": c}
                     for a, c in acoes.most_common()],
        "por_fila_humana": [{"fila": f, "rotulo": FILAS.get(f, f), "conversas": c} for f, c in filas.most_common()],
        "politicas_faltantes": [{"motivo": m, "rotulo": MOTIVOS_ROTULO[m], "conversas": c,
                                 "sugestao": SUGESTAO_POLITICA[m]} for m, c in destravaria.most_common()],
    }


def bloco_p4_historico(resultados: list[dict]) -> dict:
    """O grafo nas 4.000 conversas do trimestre: o que o agente teria feito se estivesse no ar.

    Conversas sem mensagem do cliente (abandono no bot) terminam no `classificar`: não há o que
    resolver, então os percentuais usam como base as conversas COM mensagem.
    """
    com_msg = [r for r in resultados if r["modo"] != "encerrado"]
    base = bloco_p4(com_msg)
    return {
        "conversas": len(resultados),
        "com_mensagem": len(com_msg),
        "sem_mensagem": len(resultados) - len(com_msg),
        "automatico": base["automatico"],
        "humano": base["humano"],
        "pct_automatico": frac(base["automatico"], len(com_msg)),
        "resolucao_completa_pct": base["resolucao_completa_pct"],
        "por_acao": base["por_acao"],
        "por_fila_humana": base["por_fila_humana"],
    }


def bloco_saude(origem: Path, d: pd.DataFrame) -> dict:
    """Por que existe a categoria Saúde: casos reais que a lista de tags do atendimento não enxerga."""
    sau = d[d.motivos.str.split(";").apply(lambda s: bool(set(s) & SEMPRE_HUMANO))]
    tem = lambda m: int(sau.motivos.str.split(";").apply(lambda s: m in s).sum())  # noqa: E731
    msgs = pd.read_csv(origem / "case_atendimento" / "mensagens.csv", usecols=["conversation_id", "autor", "timestamp"],
                       parse_dates=["timestamp"])
    ms = msgs[msgs.conversation_id.isin(sau.conversation_id)].sort_values("timestamp")
    primeiro = Counter()
    horas = []
    reacao = set(sau[sau.motivos.str.split(";").apply(lambda s: "reacao_adversa" in s)].conversation_id)
    for cid, g in ms.groupby("conversation_id"):
        resp = g[g.autor != "cliente"]
        primeiro[resp.autor.iloc[0] if len(resp) else "ninguem"] += 1
        if cid in reacao:
            t0 = g[g.autor == "cliente"].timestamp.min()
            humano = g[(g.autor == "agente") & (g.timestamp >= t0)].timestamp.min()
            if pd.notna(humano):
                horas.append((humano - t0).total_seconds() / 3600)
    h = pd.Series(horas)
    tags = sau.tag_agente.fillna("(sem tag)").value_counts()
    return {
        "conversas": len(sau),
        "pct_conversas": frac(len(sau), len(d)),
        "reacao_adversa": tem("reacao_adversa"),
        "duvida_saude": tem("duvida_saude"),
        "existe_tag_saude": False,
        "tags_manuais": [{"tag": t, "conversas": int(n)} for t, n in tags.items()],
        "primeira_resposta": {"bot": primeiro["bot"], "agente": primeiro["agente"], "ninguem": primeiro["ninguem"]},
        "reacao_horas_ate_humano_mediana": round(float(h.median()), 1) if len(h) else None,
        "reacao_acima_24h": int((h > 24).sum()),
        "prazo_politica_horas": 24,
    }


def bloco_metodologia(origem: Path, d: pd.DataFrame, fila: list[dict]) -> dict:
    """Números do processo, para a página Metodologia (como chegamos aos resultados)."""
    from atendimento.lote import normalizar
    msgs = pd.read_csv(origem / "case_atendimento" / "mensagens.csv")
    cli = msgs[msgs.autor == "cliente"].sort_values("timestamp").groupby("conversation_id").texto.apply(list)
    unicos = {normalizar(t) for t in cli}
    tags = d.tag_agente.dropna()
    return {
        "conversas": len(d),
        "mensagens": len(msgs),
        "mensagens_por_autor": {a: int(n) for a, n in msgs.autor.value_counts().items()},
        "conversas_com_mensagem_cliente": len(cli),
        "conversas_sem_mensagem_cliente": len(d) - len(cli),
        "textos_unicos_classificados": len(unicos),
        "economia_deduplicacao_pct": frac(len(cli) - len(unicos), len(cli)),
        "conversas_por_status": {s_: int(n) for s_, n in d.status.value_counts().items()},
        "fila_em_aberto": len(fila),
        "tags_manuais_existentes": int(tags.nunique()),
        "conversas_com_tag": len(tags),
        "custo_por_canal": {c: CUSTO_CONVERSA[c] for c in ("whatsapp", "email", "reclame_aqui")},
        "categorias_taxonomia": len(CATEGORIAS),
        "motivos_taxonomia": len(MOTIVOS_ROTULO),
    }


def gerar(origem: Path, modelo: str) -> dict:
    d = carregar_conversas(origem, modelo)
    inicio, fim = d.data_abertura.min().date(), d.data_abertura.max().date()
    return {
        "exemplo": False,
        "gerado_em": date.today().isoformat(),
        "periodo": {"inicio": inicio.isoformat(), "fim": fim.isoformat(), "dias": (fim - inicio).days + 1},
        "totais": {"conversas": len(d), "fator_expansao": FATOR_EXPANSAO,
                   "conversas_estimadas": len(d) * FATOR_EXPANSAO,
                   "custo_estimado": reais(d.custo.sum()), "marcas": d.marca.nunique()},
        "classificacao": bloco_classificacao(origem, modelo),
        "p1_por_que_procuram": bloco_p1(d),
        "p2_contatos_evitaveis": bloco_p2(d),
        "p3_atacar_primeiro": bloco_p3(d),
        "p4_sozinho_ou_pessoa": {**bloco_p4(fila := carregar_resultados(origem)),
                                 "historico": bloco_p4_historico(
                                     carregar_resultados(origem, "resultados_grafo_historico.jsonl"))},
        "saude": bloco_saude(origem, d),
        "metodologia": bloco_metodologia(origem, d, fila),
    }


# Números já registrados no CLAUDE.md: o script avisa se algum mudou.
_P1, _P2, _P4 = "p1_por_que_procuram", "p2_contatos_evitaveis", "p4_sozinho_ou_pessoa"
REGISTRADOS = {
    "conversas estimadas no trimestre": (lambda j: j["totais"]["conversas_estimadas"], 12000),
    "custo trimestral": (lambda j: j["totais"]["custo_estimado"], 108299),
    "custo Reclame Aqui": (lambda j: _item(j[_P1]["canais"], "canal", "reclame_aqui")["custo"], 51282),
    "% custo Reclame Aqui": (lambda j: round(_item(j[_P1]["canais"], "canal", "reclame_aqui")["pct_custo"], 2), 0.47),
    "acerto do agente": (lambda j: j["classificacao"]["acerto_agente"], 0.9479),
    "acerto da tag manual": (lambda j: j["classificacao"]["acerto_tag_manual"], 0.5319),
    "saúde no gabarito": (lambda j: j["classificacao"]["saude_detectada"], "14/14"),
    "fila avaliada": (lambda j: j[_P4]["fila_avaliada"], 1337),
    "automáticas": (lambda j: j[_P4]["automatico"], 784),
    "humanas": (lambda j: j[_P4]["humano"], 553),
    "resolução completa": (lambda j: round(j[_P4]["resolucao_completa_pct"], 2), 0.42),
    "custo recontato": (lambda j: _item(j[_P2]["itens"], "id", "recontato")["custo"], 28642),
    "custo evitável (sem dupla contagem)": (lambda j: j[_P2]["total_custo"], 48902),
    "política faltante: brinde": (lambda j: _item(j[_P4]["politicas_faltantes"], "motivo", "brinde_faltante")["conversas"], 88),
    "política faltante: dúvida de produto": (lambda j: _item(j[_P4]["politicas_faltantes"], "motivo", "duvida_produto")["conversas"], 85),
    "política faltante: insatisfação": (lambda j: _item(j[_P4]["politicas_faltantes"], "motivo", "insatisfacao_produto")["conversas"], 53),
    "política faltante: troca": (lambda j: _item(j[_P4]["politicas_faltantes"], "motivo", "troca_outros")["conversas"], 28),
    "histórico: automáticas": (lambda j: j[_P4]["historico"]["automatico"], 2155),
    "histórico: humanas": (lambda j: j[_P4]["historico"]["humano"], 1386),
    "histórico: % automático": (lambda j: round(j[_P4]["historico"]["pct_automatico"], 2), 0.61),
    "saúde: conversas": (lambda j: j["saude"]["conversas"], 65),
    "saúde: 1ª resposta pelo bot": (lambda j: j["saude"]["primeira_resposta"]["bot"], 58),
    "textos únicos classificados": (lambda j: j["metodologia"]["textos_unicos_classificados"], 1720),
}


def _item(lista: list[dict], chave: str, valor: str) -> dict:
    return next(x for x in lista if x[chave] == valor)


def conferir(j: dict) -> None:
    print("\nConferência com os números do CLAUDE.md:")
    for nome, (obter, esperado) in REGISTRADOS.items():
        valor = obter(j)
        ok = abs(valor - esperado) < 0.001 if isinstance(esperado, float) else valor == esperado
        print(f"  {'✓' if ok else '✗'} {nome}: {valor}" + ("" if ok else f" (registrado: {esperado})"))


def main() -> None:
    args = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    origem = Path(args.get("origem", RAIZ)).resolve()
    modelo = args.get("modelo", "gemini-3.5-flash-lite")

    j = gerar(origem, modelo)
    texto = json.dumps(j, ensure_ascii=False, indent=2) + "\n"

    msgs = pd.read_csv(origem / "case_atendimento" / "mensagens.csv").texto.dropna().tolist()
    if problemas := problemas_de_privacidade(texto, msgs):
        raise SystemExit("NÃO gravado. Problemas de privacidade:\n  " + "\n  ".join(problemas))

    SAIDA.write_text(texto, encoding="utf-8")
    p1, p4 = j["p1_por_que_procuram"], j["p4_sozinho_ou_pessoa"]
    print(f"Gravado {SAIDA.relative_to(RAIZ)} ({len(texto) / 1024:.1f} KB) a partir de {origem}")
    print(f"{j['totais']['conversas']} conversas | custo trimestral {brl(j['totais']['custo_estimado'])}")
    print("Top 3 motivos por custo:", ", ".join(f"{m['rotulo']} {brl(m['custo'])}" for m in p1["motivos"][:3]))
    print(f"Fila: {p4['automatico']} automáticas / {p4['humano']} humanas | resolução completa "
          f"{pct(p4['resolucao_completa_pct'])}")
    conferir(j)


if __name__ == "__main__":
    main()
