"""Nó 5 · checar_elegibilidade (determinístico): o caso cabe na política vigente?

TODO: implementar as políticas de parametros.md (arrependimento 7d, avaria/faltante 7d com foto,
troca de fragrância 30d, estorno, cosmetovigilância, endereço antes da separação, personalização).
"""
from atendimento.dominio.schemas import Elegibilidade
from atendimento.grafo.estado import EstadoAtendimento


def checar_elegibilidade(estado: EstadoAtendimento) -> dict:
    e = Elegibilidade(resultado="indeterminado", politica=None, justificativa="[STUB] políticas não implementadas")
    return {"elegibilidade": e, "trilha": ["checar_elegibilidade: [STUB] indeterminado"]}
