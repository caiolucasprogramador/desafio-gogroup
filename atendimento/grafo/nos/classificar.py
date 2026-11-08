"""Nó 2 · classificar: motivos, recontato, tom; motivo principal por GRAVIDADE.

Cache primeiro: se o texto (normalizado) já foi classificado no lote, usa o resultado
sem chamar o LLM. Só textos novos vão ao modelo (bloqueado se SEM_LLM=1).
"""
import os
from functools import lru_cache
from pathlib import Path

from atendimento.grafo.estado import EstadoAtendimento
from atendimento.servicos.classificacao import MODELO_PADRAO, classificar as classificar_conversa

CACHE = Path(__file__).resolve().parents[3] / "dados" / "cache_classificacao.jsonl"


@lru_cache
def _lote():
    from atendimento.lote import ClassificadorLote
    return ClassificadorLote(CACHE, modelo=MODELO_PADRAO)


def classificar(estado: EstadoAtendimento) -> dict:
    msgs = estado.get("mensagens_cliente", [])
    c, fonte = _lote().resultado(msgs), "cache"
    if c is None:
        if os.environ.get("SEM_LLM") == "1":
            raise RuntimeError("SEM_LLM=1 e a conversa não está no cache de classificação")
        c, fonte = classificar_conversa(msgs), "llm ao vivo"
    motivos = ", ".join(m.motivo for m in c.motivos) or "nenhum"
    return {"classificacao": c,
            "trilha": [f"classificar ({fonte}): motivos=[{motivos}] principal={c.motivo_principal} tom={c.tom}"]}
