"""Garantias do sistema checadas na fila REAL (substituem o antigo nó `auditar`).

Lê dados/resultados_grafo.jsonl (gerado por `python -m scripts.processar_fila`); pula se não existir.
"""
import json
from pathlib import Path

import pytest

from atendimento.dominio.parametros import LIMITE_VALOR_AUTOMATICO
from atendimento.dominio.taxonomia import SEMPRE_HUMANO
from atendimento.servicos.decisao import ACOES_COM_CUSTO

ARQ = Path(__file__).resolve().parents[1] / "dados" / "resultados_grafo.jsonl"
pytestmark = pytest.mark.skipif(not ARQ.exists(), reason="rode scripts.processar_fila antes")


@pytest.fixture(scope="module")
def fila():
    return [json.loads(l) for l in ARQ.read_text(encoding="utf-8").splitlines()]


def test_automatico_so_com_todas_as_acoes_automaticas(fila):
    assert all(all(a["modo"] == "automatico" for a in r["acoes"]) for r in fila if r["modo"] == "automatico")


def test_saude_nunca_automatica(fila):
    assert not [r["conversation_id"] for r in fila if set(r["motivos"]) & SEMPRE_HUMANO and r["modo"] != "humano"]


def test_reclame_aqui_nunca_automatico(fila):
    assert not [r for r in fila if r["canal"] == "reclame_aqui" and r["modo"] == "automatico"]


def test_acao_com_custo_so_se_elegivel_e_dentro_do_limite(fila):
    for r in fila:
        elegiveis = {e["motivo"] for e in r["elegibilidade"] if e["resultado"] == "elegivel"}
        for a in r["acoes"]:
            if a["modo"] == "automatico" and a["tipo"] in ACOES_COM_CUSTO:
                assert a["motivo"] in elegiveis, r["conversation_id"]
                assert (r["contexto"]["valor"] or 0) <= LIMITE_VALOR_AUTOMATICO, r["conversation_id"]


def test_nenhum_motivo_esquecido(fila):
    for r in fila:
        if r["acoes"]:
            assert set(r["motivos"]) == {a["motivo"] for a in r["acoes"]}, r["conversation_id"]


def test_todo_automatico_tem_rascunho_sem_dado_pessoal(fila):
    import re
    for r in fila:
        if r["modo"] == "automatico":
            assert r["rascunho_resposta"]
            assert not re.search(r"\d{3}\.\d{3}\.\d{3}-\d{2}|\d{4} \d{4} \d{4} \d{4}", r["rascunho_resposta"])
