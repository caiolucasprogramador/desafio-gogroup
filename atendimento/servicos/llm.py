"""Fábrica de LLMs independente de provedor: o nome do modelo decide (gemini*/gemma* → Google, resto → Groq).

Centraliza também o tratamento de rate limit, que cada provedor sinaliza de um jeito.
"""
import os
import re

from pydantic import BaseModel


def provedor(modelo: str) -> str:
    return "google" if modelo.startswith(("gemini", "gemma")) else "groq"


class ChaveAusente(RuntimeError):
    """A variável de ambiente com a chave do provedor não está definida (ex.: faltou cadastrar na Vercel)."""

    def __init__(self, variavel: str):
        self.variavel = variavel
        super().__init__(f"variável de ambiente {variavel} não configurada")


def _chave(variavel: str) -> str:
    valor = os.environ.get(variavel, "").strip()
    if not valor:
        raise ChaveAusente(variavel)
    return valor


def criar_chat(modelo: str, temperatura: float = 0, max_retries: int = 0):
    if provedor(modelo) == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=modelo, temperature=temperatura, max_retries=max_retries,
                                      google_api_key=_chave("GEMINI_API_KEY"))
    _chave("GROQ_API_KEY")  # o ChatGroq lê a variável sozinho; checamos antes para dar erro claro
    from langchain_groq import ChatGroq
    extra = {"reasoning_effort": "low"} if "gpt-oss" in modelo else {}
    return ChatGroq(model=modelo, temperature=temperatura, max_retries=max_retries, **extra)


def criar_estruturado(modelo: str, schema: type[BaseModel], max_retries: int = 0):
    """LLM que devolve instância de `schema` (JSON Schema nativo do provedor)."""
    chat = criar_chat(modelo, max_retries=max_retries)
    if provedor(modelo) == "groq":
        return chat.with_structured_output(schema, method="json_schema", strict=True)
    return chat.with_structured_output(schema, method="json_schema")


def eh_rate_limit(erro: Exception) -> bool:
    s = str(erro)
    return "429" in s or "RESOURCE_EXHAUSTED" in s or "rate limit" in s.lower()


def eh_cota_diaria(erro: Exception) -> bool:
    s = str(erro)
    return "tokens per day" in s or "PerDay" in s or "per day" in s.lower()


def espera_sugerida(erro: Exception, padrao: float = 20) -> float:
    """Segundos sugeridos pelo provedor ('try again in 1m2.5s' na Groq, 'retryDelay': '12s' no Google)."""
    s = str(erro)
    if m := re.search(r"try again in (?:(\d+)m)?([\d.]+)s", s):
        return int(m.group(1) or 0) * 60 + float(m.group(2)) + 1
    if m := re.search(r"retry(?:Delay| in)['\": ]+([\d.]+)s", s):
        return float(m.group(1)) + 1
    return padrao


def eh_transitorio(erro: Exception) -> bool:
    """Falha do servidor (sobrecarga, timeout): esperar e repetir o MESMO pedido resolve."""
    s = str(erro)
    return any(k in s for k in ("503", "500", "502", "504", "UNAVAILABLE", "overloaded", "high demand", "timed out"))


# --- Medição de uso ----------------------------------------------------------------
import json  # noqa: E402
from contextlib import contextmanager  # noqa: E402
from datetime import datetime  # noqa: E402
from pathlib import Path  # noqa: E402

from langchain_core.callbacks import get_usage_metadata_callback  # noqa: E402

ARQUIVO_USO = Path(__file__).resolve().parents[2] / "dados" / "uso_llm.jsonl"


@contextmanager
def medir_uso(etapa: str):
    """Envolve chamadas a LLM e registra tokens por modelo em dados/uso_llm.jsonl.

    with medir_uso("classificacao_lote"):
        llm.invoke(...)
    """
    with get_usage_metadata_callback() as cb:
        yield cb
    if cb.usage_metadata:
        try:
            ARQUIVO_USO.parent.mkdir(exist_ok=True)
            arquivo = ARQUIVO_USO.open("a", encoding="utf-8")
        except OSError:  # disco somente leitura (ex.: Vercel): o registro é só para uso local
            return
        with arquivo as f:
            for modelo, uso in cb.usage_metadata.items():
                f.write(json.dumps({
                    "quando": datetime.now().isoformat(timespec="seconds"), "etapa": etapa, "modelo": modelo,
                    "entrada": uso.get("input_tokens", 0), "saida": uso.get("output_tokens", 0),
                    "total": uso.get("total_tokens", 0),
                }) + "\n")
