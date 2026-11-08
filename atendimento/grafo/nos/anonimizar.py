"""Nó 1 · anonimizar (determinístico): mascara CPF, cartão, telefone e e-mail antes de qualquer LLM."""
from atendimento.grafo.estado import EstadoAtendimento
from atendimento.servicos.anonimizacao import anonimizar as mascarar


def anonimizar(estado: EstadoAtendimento) -> dict:
    originais = estado.get("mensagens_cliente", [])
    mascaradas = [mascarar(m) for m in originais]
    n = sum(a != b for a, b in zip(originais, mascaradas))
    return {"mensagens_cliente": mascaradas, "trilha": [f"anonimizar: {n} mensagem(ns) com dado pessoal mascarado"]}
