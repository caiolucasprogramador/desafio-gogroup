"""API pública de demonstração: roda o grafo de atendimento numa mensagem digitada.

    uvicorn main:app --reload        (main.py na raiz reexporta este app; é o que a Vercel procura)

Rotas:
    GET  /…              → arquivos de public/ (index.html, diagnostico.html, diagnostico.json);
                           na Vercel, servidos pelo CDN antes de chegar ao Python
    GET  /api/exemplos   → mensagens de exemplo (escritas à mão, não vêm do case)
    GET  /api/opcoes     → valores aceitos no pedido simulado
    POST /api/atender    → roda o grafo e devolve classificação, prioridade, elegibilidade,
                           decisão, ação (resposta ou dossiê) e a trilha

Nenhum dado do case é lido aqui: o contexto vem do pedido simulado (ver enriquecer).
"""
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from atendimento.api.exemplos import EXEMPLOS
from atendimento.api.limite import Limitador
from atendimento.dominio.parametros import LIMITE_VALOR_AUTOMATICO
from atendimento.dominio.taxonomia import MOTIVO_PARA_CATEGORIA

RAIZ = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ / ".env")

from atendimento.grafo.fluxo import grafo  # noqa: E402  (depois do .env: os clientes LLM leem as chaves)
from atendimento.servicos.llm import eh_cota_diaria, eh_rate_limit  # noqa: E402

PUBLICO = RAIZ / "public"
MARCAS = ["Gocase", "Kokeshi", "Ápice", "Barbour's", "Lescent", "Rituária", "By Samia", "Yenzah", "Auá"]
STATUS = ["aguardando_pagamento", "em_separacao", "em_transito", "atrasado", "entregue"]
NOS = ["anonimizar", "classificar", "enriquecer", "priorizar", "checar_elegibilidade",
       "regras_fixas", "decidir", "agir", "escalar_humano"]

app = FastAPI(title="Agente de Atendimento · Desafio Gogroup", version="1.0")
limitador = Limitador()


class PedidoSimulado(BaseModel):
    canal: Literal["whatsapp", "email", "reclame_aqui"] = "whatsapp"
    marca: str = "Gocase"
    status_entrega: Literal["aguardando_pagamento", "em_separacao", "em_transito", "atrasado", "entregue"] | None = None
    dias_desde_pedido: int | None = Field(default=None, ge=0, le=365)
    valor: float | None = Field(default=None, ge=0, le=10_000)
    contatos_anteriores_pedido: int = Field(default=0, ge=0, le=20)

    @field_validator("marca")
    @classmethod
    def marca_valida(cls, v: str) -> str:
        if v not in MARCAS:
            raise ValueError(f"marca deve ser uma de {MARCAS}")
        return v


class PedidoAtendimento(BaseModel):
    mensagens: list[str] = Field(min_length=1, max_length=5)
    pedido: PedidoSimulado = PedidoSimulado()
    redacao_llm: bool = False

    @field_validator("mensagens")
    @classmethod
    def mensagens_validas(cls, v: list[str]) -> list[str]:
        v = [m.strip() for m in v if m and m.strip()]
        if not v:
            raise ValueError("escreva ao menos uma mensagem")
        if any(len(m) > 1000 for m in v):
            raise ValueError("cada mensagem pode ter no máximo 1000 caracteres")
        return v


def _no(linha: str) -> str:
    return linha.split(":")[0].split(" ")[0]


def _resposta(estado: dict) -> dict:
    """Estado final do grafo → JSON para a tela (seis blocos + trilha)."""
    c, p, e = estado.get("classificacao"), estado.get("prioridade"), estado.get("elegibilidade")
    d, a, ctx = estado.get("decisao"), estado.get("acao"), estado.get("contexto")
    trilha = estado.get("trilha", [])
    return {
        "mensagens_anonimizadas": estado.get("mensagens_cliente", []),
        "caminho": [_no(t) for t in trilha],
        "classificacao": c and {
            "categoria_principal": c.categoria_principal,
            "motivo_principal": c.motivo_principal,
            "motivos": [{"motivo": m.motivo, "categoria": MOTIVO_PARA_CATEGORIA.get(m.motivo),
                         "evidencia": m.evidencia} for m in c.motivos],
            "tom": c.tom, "recontato": c.recontato, "confianca": c.confianca,
            "origem": c.origem, "modelo": c.modelo,
        },
        "contexto": ctx and ctx.model_dump(),
        "prioridade": p and p.model_dump(),
        "elegibilidade": e and e.model_dump(),
        "decisao": d and {
            "modo": d.modo, "fila_destino": d.fila_destino, "justificativa": d.justificativa,
            "acoes": [x.model_dump() for x in d.acoes],
        },
        "acao": a and {
            "destino": a.destino,
            "resposta_cliente": a.rascunho_resposta,
            "origem_resposta": a.payload.get("origem_rascunho") if a.destino == "automatico" else None,
            "dossie": a.payload if a.destino == "fila_humana" else None,
        },
        "trilha": trilha,
    }


@app.get("/api/exemplos")
def exemplos() -> list[dict]:
    return EXEMPLOS


@app.get("/api/opcoes")
def opcoes() -> dict:
    return {"marcas": MARCAS, "status_entrega": STATUS, "canais": ["whatsapp", "email", "reclame_aqui"],
            "nos": NOS, "limite_valor_automatico": LIMITE_VALOR_AUTOMATICO}


@app.post("/api/atender")
def atender(corpo: PedidoAtendimento, request: Request) -> dict:
    recusa = limitador.permitir(request.client.host if request.client else "?")
    if recusa:
        raise HTTPException(429, recusa)
    p = corpo.pedido
    entrada = {
        "conversation_id": "DEMO", "canal": p.canal, "marca": p.marca, "status_conversa": "pendente",
        "data_abertura": "", "mensagens_cliente": corpo.mensagens, "redacao_llm": corpo.redacao_llm,
        "pedido_simulado": p.model_dump(include={"status_entrega", "dias_desde_pedido", "valor",
                                                 "contatos_anteriores_pedido"}),
        "trilha": [],
    }
    try:
        estado = grafo.invoke(entrada)
    except Exception as erro:  # falha do LLM de classificação (cota, rede, chave)
        if eh_cota_diaria(erro) or eh_rate_limit(erro):
            raise HTTPException(503, "cota gratuita do modelo de classificação esgotada; tente mais tarde")
        raise HTTPException(502, f"falha ao processar: {type(erro).__name__}")
    return _resposta(estado)


# Montado por ÚLTIMO: as rotas /api/* acima têm precedência. html=True serve index.html em "/".
# check_dir=False: na Vercel a pasta pode não estar dentro da função (o CDN já a serve).
app.mount("/", StaticFiles(directory=PUBLICO, html=True, check_dir=False), name="publico")
