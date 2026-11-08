"""API de demonstração: o grafo inteiro roda com o pedido simulado, sem CSV e sem LLM.

O LLM de classificação é trocado por uma resposta fixa (monkeypatch), então os testes
verificam o caminho determinístico: elegibilidade, decisão, resposta e dossiê.
"""
import importlib

import pytest
from fastapi.testclient import TestClient

from atendimento.api import app as modulo_app
from atendimento.api.limite import Limitador
from atendimento.servicos import dados
from tests.conftest import classif

# o pacote nos/ exporta a FUNÇÃO classificar; aqui queremos o MÓDULO
no_classificar = importlib.import_module("atendimento.grafo.nos.classificar")


@pytest.fixture
def cliente(monkeypatch):
    estado = {"motivos": ("arrependimento",)}

    class SemCache:
        def resultado(self, msgs):
            return None

    monkeypatch.setattr(no_classificar, "_lote", lambda: SemCache())
    monkeypatch.setattr(no_classificar, "classificar_conversa", lambda msgs: classif(*estado["motivos"]))
    monkeypatch.setattr(modulo_app, "limitador", Limitador(por_minuto=100))

    def proibido(*a, **k):
        raise AssertionError("a API não pode ler os CSVs do case")
    for f in ("pedidos", "conversas", "mensagens"):
        monkeypatch.setattr(dados, f, proibido)

    c = TestClient(modulo_app.app)
    c.motivos = lambda *m: estado.update(motivos=m)
    return c


def _pedido(**extra):
    return {"canal": "whatsapp", "marca": "Kokeshi", "status_entrega": "em_transito",
            "dias_desde_pedido": 2, "valor": 129.9, "contatos_anteriores_pedido": 0} | extra


def test_arrependimento_recente_vira_reembolso_automatico(cliente):
    r = cliente.post("/api/atender", json={"mensagens": ["quero cancelar"], "pedido": _pedido()})
    assert r.status_code == 200
    j = r.json()
    assert j["decisao"]["modo"] == "automatico"
    assert j["acao"]["destino"] == "automatico" and "129,90" in j["acao"]["resposta_cliente"]
    assert j["caminho"][-1] == "agir" and "escalar_humano" not in j["caminho"]
    assert j["classificacao"]["motivo_principal"] == "arrependimento"
    assert set(j["prioridade"]["contribuicoes"]) == {"gravidade", "canal", "sla", "recontato", "valor", "tom"}


def test_saude_vai_para_responsavel_tecnica_com_dossie(cliente):
    cliente.motivos("reacao_adversa")
    j = cliente.post("/api/atender", json={"mensagens": ["meu rosto ficou vermelho"], "pedido": _pedido()}).json()
    assert j["decisao"]["modo"] == "humano" and j["decisao"]["fila_destino"] == "responsavel_tecnica"
    assert j["acao"]["dossie"]["fila"] == "responsavel_tecnica" and j["acao"]["resposta_cliente"] is None
    assert j["prioridade"]["topo_da_fila"] is True


def test_reclame_aqui_sempre_humano(cliente):
    j = cliente.post("/api/atender", json={"mensagens": ["quero cancelar"],
                                           "pedido": _pedido(canal="reclame_aqui")}).json()
    assert j["decisao"]["modo"] == "humano" and j["decisao"]["fila_destino"] == "reclame_aqui"


def test_sem_pedido_pede_informacao(cliente):
    j = cliente.post("/api/atender", json={"mensagens": ["quero cancelar"],
                                           "pedido": _pedido(status_entrega=None)}).json()
    assert j["contexto"]["order_id"] is None
    assert any(a["tipo"] == "solicitar_informacoes" for a in j["decisao"]["acoes"])


def test_anonimiza_antes_do_llm(cliente):
    j = cliente.post("/api/atender", json={"mensagens": ["meu cpf é 123.456.789-09"], "pedido": _pedido()}).json()
    assert "123.456.789-09" not in j["mensagens_anonimizadas"][0]


def test_validacao_e_limite(cliente, monkeypatch):
    assert cliente.post("/api/atender", json={"mensagens": ["   "]}).status_code == 422
    assert cliente.post("/api/atender", json={"mensagens": ["x" * 1001]}).status_code == 422
    assert cliente.post("/api/atender", json={"mensagens": ["oi"], "pedido": _pedido(marca="Outra")}).status_code == 422
    monkeypatch.setattr(modulo_app, "limitador", Limitador(por_minuto=1))
    assert cliente.post("/api/atender", json={"mensagens": ["oi"], "pedido": _pedido()}).status_code == 200
    assert cliente.post("/api/atender", json={"mensagens": ["oi"], "pedido": _pedido()}).status_code == 429


def test_exemplos_e_pagina(cliente):
    assert len(cliente.get("/api/exemplos").json()) >= 5
    assert "Agente de Atendimento" in cliente.get("/").text
