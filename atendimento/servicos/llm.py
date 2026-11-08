"""Fábrica de LLMs independente de provedor: o nome do modelo decide (gemini*/gemma* → Google, resto → Groq).

Centraliza também o tratamento de rate limit, que cada provedor sinaliza de um jeito.
"""
import os
import re

from pydantic import BaseModel


def provedor(modelo: str) -> str:
    return "google" if modelo.startswith(("gemini", "gemma")) else "groq"


def criar_chat(modelo: str, temperatura: float = 0, max_retries: int = 0):
    if provedor(modelo) == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=modelo, temperature=temperatura, max_retries=max_retries,
                                      google_api_key=os.environ["GEMINI_API_KEY"])
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
