"""public/diagnostico.json: contrato (docs/plano-paralelo.md, seção 3) e privacidade.

O JSON é versionado e publicado, então estes testes rodam em qualquer máquina, sem os dados.
Só a checagem de "trecho de mensagem copiado" precisa do case local (pulada sem ele).
"""
import json
from pathlib import Path

import pytest

from atendimento.dominio.rotulos import ACOES, CANAIS, CATEGORIAS, FILAS, MOTIVOS_ROTULO
from atendimento.dominio.taxonomia import GRAVIDADE, MOTIVO_PARA_CATEGORIA
from scripts.gerar_diagnostico import problemas_de_privacidade

RAIZ = Path(__file__).resolve().parents[1]
CAMINHO = RAIZ / "public" / "diagnostico.json"
MENSAGENS = RAIZ / "case_atendimento" / "mensagens.csv"

# Chaves obrigatórias → tipo. Listas: tipo de cada campo dos itens.
NUM = (int, float)
CONTRATO = {
    "exemplo": bool, "gerado_em": str,
    "periodo": {"inicio": str, "fim": str, "dias": int},
    "totais": {"conversas": int, "fator_expansao": int, "conversas_estimadas": int, "custo_estimado": NUM,
               "marcas": int},
    "classificacao": {"amostra_gabarito": int, "acerto_agente": NUM, "acerto_tag_manual": NUM,
                      "recall_motivos": NUM, "saude_detectada": str, "modelo": str, "observacao": str},
    "p1_por_que_procuram": {
        "categorias": [{"categoria": str, "rotulo": str, "conversas": int, "pct_conversas": NUM,
                        "custo": NUM, "pct_custo": NUM}],
        "motivos": [{"motivo": str, "rotulo": str, "categoria": str, "conversas": int, "pct_conversas": NUM,
                     "custo": NUM, "pct_custo": NUM, "gravidade": int}],
        "canais": [{"canal": str, "rotulo": str, "conversas": int, "pct_conversas": NUM, "custo_unitario": NUM,
                    "custo": NUM, "pct_custo": NUM}],
    },
    "p2_contatos_evitaveis": {"total_custo": NUM, "itens": [{"id": str, "rotulo": str, "conversas": int,
                                                             "custo": NUM, "como_evitar": str}]},
    "p3_atacar_primeiro": {"criterio": str, "itens": [{"rank": int, "foco": str, "porque": str,
                                                       "conversas": int, "custo": NUM}]},
    "p4_sozinho_ou_pessoa": {
        "fila_avaliada": int, "automatico": int, "humano": int, "resolucao_completa_pct": NUM,
        "por_acao": [{"acao": str, "rotulo": str, "modo": str, "conversas": int}],
        "por_fila_humana": [{"fila": str, "rotulo": str, "conversas": int}],
        "politicas_faltantes": [{"motivo": str, "rotulo": str, "conversas": int, "sugestao": str}],
        "historico": {"conversas": int, "com_mensagem": int, "sem_mensagem": int, "automatico": int, "humano": int,
                      "pct_automatico": NUM, "resolucao_completa_pct": NUM,
                      "por_acao": [{"acao": str, "rotulo": str, "modo": str, "conversas": int}],
                      "por_fila_humana": [{"fila": str, "rotulo": str, "conversas": int}]},
    },
    "saude": {"conversas": int, "pct_conversas": NUM, "reacao_adversa": int, "duvida_saude": int,
              "existe_tag_saude": bool, "tags_manuais": [{"tag": str, "conversas": int}],
              "primeira_resposta": {"bot": int, "agente": int, "ninguem": int},
              "reacao_horas_ate_humano_mediana": NUM, "reacao_acima_24h": int, "prazo_politica_horas": int},
    "metodologia": {"conversas": int, "mensagens": int, "mensagens_por_autor": dict,
                    "conversas_com_mensagem_cliente": int, "conversas_sem_mensagem_cliente": int,
                    "textos_unicos_classificados": int, "economia_deduplicacao_pct": NUM,
                    "conversas_por_status": dict, "fila_em_aberto": int, "tags_manuais_existentes": int,
                    "conversas_com_tag": int, "custo_por_canal": dict, "categorias_taxonomia": int,
                    "motivos_taxonomia": int},
}


@pytest.fixture(scope="module")
def texto() -> str:
    return CAMINHO.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def j(texto) -> dict:
    return json.loads(texto)


def _conferir(valor, esperado, caminho: str) -> list[str]:
    if isinstance(esperado, dict):
        if not isinstance(valor, dict):
            return [f"{caminho}: esperado objeto"]
        return [e for k, tipo in esperado.items()
                for e in (_conferir(valor[k], tipo, f"{caminho}.{k}") if k in valor else [f"{caminho}.{k}: falta"])]
    if isinstance(esperado, list):
        if not isinstance(valor, list) or not valor:
            return [f"{caminho}: esperada lista não vazia"]
        return [e for i, item in enumerate(valor) for e in _conferir(item, esperado[0], f"{caminho}[{i}]")]
    # bool é subclasse de int em Python: não aceitar True onde se espera número
    if isinstance(valor, bool) and esperado is not bool:
        return [f"{caminho}: booleano onde se espera {esperado}"]
    return [] if isinstance(valor, esperado) else [f"{caminho}: {type(valor).__name__}, esperado {esperado}"]


def test_contrato_chaves_e_tipos(j):
    assert _conferir(j, CONTRATO, "$") == []


def test_dados_reais_e_coerentes(j):
    assert j["exemplo"] is False, "rode scripts.gerar_diagnostico: o JSON ainda é o de exemplo"
    t, p1, p4 = j["totais"], j["p1_por_que_procuram"], j["p4_sozinho_ou_pessoa"]
    assert t["conversas_estimadas"] == t["conversas"] * t["fator_expansao"]
    for lista in ("categorias", "motivos", "canais"):
        itens = p1[lista]
        assert sum(x["conversas"] for x in itens) == t["conversas"], lista
        for campo in ("pct_conversas", "pct_custo"):
            assert sum(x[campo] for x in itens) == pytest.approx(1, abs=0.01), f"{lista}.{campo}"
        assert sum(x["custo"] for x in itens) == pytest.approx(t["custo_estimado"], abs=len(itens)), lista
    assert p4["automatico"] + p4["humano"] == p4["fila_avaliada"]
    assert sum(x["conversas"] for x in p4["por_acao"]) == p4["automatico"]
    assert sum(x["conversas"] for x in p4["por_fila_humana"]) == p4["humano"]
    assert [x["rank"] for x in j["p3_atacar_primeiro"]["itens"]] == list(range(1, len(j["p3_atacar_primeiro"]["itens"]) + 1))
    # o total evitável desconta sobreposições: nunca maior que a soma dos itens
    p2 = j["p2_contatos_evitaveis"]
    assert p2["total_custo"] <= sum(x["custo"] for x in p2["itens"])
    fracoes = [j["classificacao"][k] for k in ("acerto_agente", "acerto_tag_manual", "recall_motivos")]
    assert all(0 <= x <= 1 for x in fracoes + [p4["resolucao_completa_pct"]])


def test_historico_saude_e_metodologia_coerentes(j):
    t, h, sau, m = j["totais"], j["p4_sozinho_ou_pessoa"]["historico"], j["saude"], j["metodologia"]
    # histórico: as 4.000 conversas, separadas em sem mensagem / automático / humano
    assert h["conversas"] == t["conversas"] == m["conversas"]
    assert h["com_mensagem"] + h["sem_mensagem"] == h["conversas"]
    assert h["automatico"] + h["humano"] == h["com_mensagem"]
    assert sum(x["conversas"] for x in h["por_acao"]) == h["automatico"]
    assert sum(x["conversas"] for x in h["por_fila_humana"]) == h["humano"]
    # a fila em aberto é um subconjunto do histórico
    assert j["p4_sozinho_ou_pessoa"]["fila_avaliada"] == m["fila_em_aberto"] <= h["com_mensagem"]
    # saúde: toda conversa de saúde tem uma tag manual, e nenhuma delas é "Saúde"
    assert sum(x["conversas"] for x in sau["tags_manuais"]) == sau["conversas"]
    assert sau["existe_tag_saude"] is False and all("saúde" not in x["tag"].lower() for x in sau["tags_manuais"])
    assert sum(sau["primeira_resposta"].values()) == sau["conversas"]
    assert max(sau["reacao_adversa"], sau["duvida_saude"]) <= sau["conversas"] <= sau["reacao_adversa"] + sau["duvida_saude"]
    # metodologia: funil fecha
    assert m["conversas_com_mensagem_cliente"] + m["conversas_sem_mensagem_cliente"] == m["conversas"]
    assert m["conversas_com_mensagem_cliente"] == h["com_mensagem"]
    assert m["textos_unicos_classificados"] <= m["conversas_com_mensagem_cliente"]
    assert sum(m["mensagens_por_autor"].values()) == m["mensagens"]
    assert sum(m["conversas_por_status"].values()) == m["conversas"]


def test_listas_ordenadas_por_custo(j):
    for lista in ("categorias", "motivos", "canais"):
        custos = [x["custo"] for x in j["p1_por_que_procuram"][lista]]
        assert custos == sorted(custos, reverse=True), lista


def test_codigos_e_rotulos_batem_com_o_dominio(j):
    p1, p4 = j["p1_por_que_procuram"], j["p4_sozinho_ou_pessoa"]
    for c in p1["categorias"]:
        assert c["rotulo"] == CATEGORIAS[c["categoria"]]
    for m in p1["motivos"]:
        assert m["rotulo"] == MOTIVOS_ROTULO[m["motivo"]]
        assert m["categoria"] == MOTIVO_PARA_CATEGORIA[m["motivo"]] and m["gravidade"] == GRAVIDADE[m["motivo"]]
    for c in p1["canais"]:
        assert c["rotulo"] == CANAIS[c["canal"]]
    assert all(a["acao"] in ACOES and a["modo"] == "automatico" for a in p4["por_acao"])
    assert all(f["fila"] in FILAS for f in p4["por_fila_humana"])
    assert all(p["motivo"] in MOTIVOS_ROTULO for p in p4["politicas_faltantes"])


def test_privacidade_sem_ids_nem_dados_pessoais(texto):
    assert problemas_de_privacidade(texto) == []


def test_detector_de_privacidade_pega_vazamentos():
    """O teste acima só vale se o detector funciona: aqui ele precisa reclamar."""
    for vazamento in ("CV910003", "CL430349", "GB8100010", "M0000001", "fulana@exemplo.com",
                      "(85) 99999-1234", "123.456.789-09", "4111 1111 1111 1111"):
        assert problemas_de_privacidade(json.dumps({"x": f"texto {vazamento} aqui"})), vazamento
    msg = "o meu pedido chegou com a tampa quebrada e vazando tudo"
    assert problemas_de_privacidade(json.dumps({"x": msg}), [msg])
    assert not problemas_de_privacidade(json.dumps({"x": "Atraso na entrega"}), [msg])


@pytest.mark.skipif(not MENSAGENS.exists(), reason="sem os dados do case nesta máquina")
def test_nenhum_trecho_de_mensagem(texto):
    import pandas as pd
    msgs = pd.read_csv(MENSAGENS).texto.dropna().tolist()
    assert problemas_de_privacidade(texto, msgs) == []
