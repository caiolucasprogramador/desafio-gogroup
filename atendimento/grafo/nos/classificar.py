"""Nó 2 · classificar (LLM): motivos, recontato, tom; motivo principal por GRAVIDADE."""
from atendimento.grafo.estado import EstadoAtendimento
from atendimento.servicos.classificacao import classificar as classificar_conversa


def classificar(estado: EstadoAtendimento) -> dict:
    c = classificar_conversa(estado.get("mensagens_cliente", []))
    motivos = ", ".join(m.motivo for m in c.motivos) or "nenhum"
    return {"classificacao": c,
            "trilha": [f"classificar ({c.origem}): motivos=[{motivos}] principal={c.motivo_principal} tom={c.tom}"]}
