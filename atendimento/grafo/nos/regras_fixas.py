"""Nó 6 · regras_fixas (determinístico): casos que NUNCA são decididos pelo LLM.

Se uma regra dispara, grava `decisao` (modo=humano) e o roteamento vai para escalar_humano.
"""
from atendimento.dominio.schemas import Decisao
from atendimento.dominio.taxonomia import SEMPRE_HUMANO
from atendimento.grafo.estado import EstadoAtendimento


def regras_fixas(estado: EstadoAtendimento) -> dict:
    motivos = {m.motivo for m in estado["classificacao"].motivos}
    if saude := motivos & SEMPRE_HUMANO:
        d = Decisao(modo="humano", origem="regra", acao_proposta="encaminhar_responsavel_tecnica",
                    justificativa=f"Saúde ({', '.join(sorted(saude))}): exige responsável técnica e "
                                  "registro de cosmetovigilância em até 24h.")
    elif estado.get("canal") == "reclame_aqui":
        d = Decisao(modo="humano", origem="regra", acao_proposta="resposta_publica_analista",
                    justificativa="Reclame Aqui: resposta pública e risco reputacional.")
    else:
        return {"trilha": ["regras_fixas: nenhuma regra disparou → decisão pelo LLM"]}
    return {"decisao": d, "trilha": [f"regras_fixas: {d.justificativa}"]}
