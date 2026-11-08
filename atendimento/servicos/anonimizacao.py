"""Mascara dados pessoais (LGPD) antes de qualquer envio a LLM ou publicação."""
import re

PADROES: list[tuple[str, re.Pattern]] = [
    ("[CARTAO]", re.compile(r"\b\d{4}[ .-]?\d{4}[ .-]?\d{4}[ .-]?\d{4}\b")),
    ("[CPF]", re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")),
    ("[TELEFONE]", re.compile(r"\(?\b\d{2}\)?\s?9?\d{4}-?\d{4}\b")),
    ("[EMAIL]", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")),
]


def anonimizar(texto: str) -> str:
    for marcador, padrao in PADROES:
        texto = padrao.sub(marcador, texto)
    return texto
