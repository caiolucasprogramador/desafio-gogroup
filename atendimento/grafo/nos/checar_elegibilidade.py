"""Nó 5 · checar_elegibilidade (determinístico): cada motivo contra a política vigente.

Resultados: elegivel | inelegivel | indeterminado (falta dado: lista o que pedir) | sem_politica.
Regras em servicos/elegibilidade.py; políticas em dominio/politicas.py.
"""
from atendimento.grafo.estado import EstadoAtendimento
from atendimento.servicos.elegibilidade import avaliar, resumir


def checar_elegibilidade(estado: EstadoAtendimento) -> dict:
    e = avaliar(estado["classificacao"], estado["contexto"], estado.get("marca", ""),
                estado.get("mensagens_cliente", []))
    return {"elegibilidade": e, "trilha": [f"checar_elegibilidade: {resumir(e)}"]}
