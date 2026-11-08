"""Nó 7 · decidir (determinístico): tabela de decisão por motivo.

- Motivo com política → usa a elegibilidade: elegível executa (até o limite de valor),
  indeterminado pede o que falta, inelegível explica.
- Rastreio/atraso → regra operacional pelo status de entrega.
- Demais motivos sem regra → fila humana adequada (financeiro, comercial, atendimento...).
Conversa é automática só se TODOS os motivos forem automáticos. Regras em servicos/decisao.py.
"""
from atendimento.grafo.estado import EstadoAtendimento
from atendimento.servicos.decisao import decidir as decidir_conversa


def decidir(estado: EstadoAtendimento) -> dict:
    d = decidir_conversa(estado["classificacao"], estado["contexto"], estado["elegibilidade"])
    acoes = "; ".join(f"{a.motivo}→{a.tipo}[{a.modo}{'/' + a.fila if a.fila else ''}]" for a in d.acoes)
    return {"decisao": d,
            "trilha": [f"decidir: {d.modo.upper()} | {acoes}"]}
