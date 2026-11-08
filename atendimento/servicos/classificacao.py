"""Nó `classificar`: motivos do contato a partir apenas das mensagens do cliente.

- Conversa sem mensagem do cliente → regra (sem_conteudo), sem LLM.
- Demais → LLM com saída estruturada (json_schema estrito).
- motivo_principal é derivado por regra, não pelo LLM, para ser determinístico.
"""
from langchain_core.messages import HumanMessage, SystemMessage

from atendimento.servicos.anonimizacao import anonimizar
from atendimento.servicos.llm import criar_estruturado
from atendimento.dominio.schemas import Classificacao, ClassificacaoLLM
from atendimento.dominio.taxonomia import GRAVIDADE, MOTIVO_PARA_CATEGORIA, TAXONOMIA

MODELO_PADRAO = "gemini-3.5-flash-lite"  # escolhido no gabarito (ver README)


def _descrever_taxonomia() -> str:
    linhas = []
    for categoria, motivos in TAXONOMIA.items():
        linhas.append(f"[{categoria}]")
        linhas += [f"- {m}: {d}" for m, d in motivos.items() if m != "sem_conteudo"]
    return "\n".join(linhas)


PROMPT_SISTEMA = f"""Você classifica contatos de clientes do atendimento de e-commerce (Gocase e marcas GoBeauté).
Leia SOMENTE as mensagens do cliente e identifique TODOS os motivos do contato.

Taxonomia:
{_descrever_taxonomia()}

Regras:
1. Uma conversa pode ter vários motivos (ex.: "...E outra coisa: ..."). Liste todos, na ordem em que aparecem.
2. Qualquer relato de reação física após usar o produto é reacao_adversa, mesmo que o cliente peça troca ou ressarcimento.
3. Perguntas sobre uso na gravidez, amamentação ou por crianças são duvida_saude, não duvida_produto.
4. rastreio_status: o cliente quer saber onde está o pedido. atraso: o cliente afirma que o prazo venceu.
5. compra_duplicada_cliente: o CLIENTE comprou duas vezes. cobranca_duplicada: a EMPRESA cobrou duas vezes.
6. brinde_faltante é diferente de item_faltante: brinde/mimo de promoção não é produto comprado.
7. Sarcasmo ("que maravilha, chegou vazando") é reclamação, nunca elogio.
8. A evidência deve ser um trecho copiado literalmente da mensagem do cliente."""


def motivo_principal(motivos: list[str]) -> str:
    """O motivo mais grave (GRAVIDADE); em empate, o primeiro mencionado."""
    if not motivos:
        return "outro"
    return max(motivos, key=lambda m: (GRAVIDADE[m], -motivos.index(m)))


def montar_entrada(mensagens_cliente: list[str]) -> str:
    return "\n".join(f"Cliente: {anonimizar(t)}" for t in mensagens_cliente)


def criar_classificador(modelo: str = MODELO_PADRAO):
    return criar_estruturado(modelo, ClassificacaoLLM, max_retries=6)


def finalizar(saida: ClassificacaoLLM, modelo: str) -> Classificacao:
    motivos = list(dict.fromkeys(m.motivo for m in saida.motivos))  # dedup mantendo ordem
    principal = motivo_principal(motivos)
    return Classificacao(
        **saida.model_dump(),
        motivo_principal=principal,
        categoria_principal=MOTIVO_PARA_CATEGORIA[principal],
        origem="llm",
        modelo=modelo,
    )


def classificacao_sem_conteudo() -> Classificacao:
    return Classificacao(
        motivos=[], recontato=False, tom="neutro", confianca="alta",
        motivo_principal="sem_conteudo", categoria_principal="outros", origem="regra",
    )


def classificar_lote(conversas: list[list[str]], modelo: str = MODELO_PADRAO,
                     max_concorrencia: int = 4) -> list[Classificacao | Exception]:
    """Classifica várias conversas; cada item é a lista de mensagens do cliente."""
    clf = criar_classificador(modelo)
    resultados: list[Classificacao | Exception | None] = [None] * len(conversas)
    idx_llm, entradas = [], []
    for i, msgs in enumerate(conversas):
        if not msgs:
            resultados[i] = classificacao_sem_conteudo()
        else:
            idx_llm.append(i)
            entradas.append([SystemMessage(PROMPT_SISTEMA), HumanMessage(montar_entrada(msgs))])
    saidas = clf.batch(entradas, config={"max_concurrency": max_concorrencia}, return_exceptions=True)
    for i, s in zip(idx_llm, saidas):
        resultados[i] = s if isinstance(s, Exception) else finalizar(s, modelo)
    return resultados


def classificar(mensagens_cliente: list[str], modelo: str = MODELO_PADRAO) -> Classificacao:
    """Classifica uma única conversa (uso ao vivo, dentro do grafo)."""
    resultado = classificar_lote([mensagens_cliente], modelo=modelo, max_concorrencia=1)[0]
    if isinstance(resultado, Exception):
        raise resultado
    return resultado
