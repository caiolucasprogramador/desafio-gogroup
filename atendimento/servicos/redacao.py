"""Redação com LLM: reescreve o rascunho do template em tom natural, sem mudar o conteúdo.

O LLM NÃO decide nada: recebe o rascunho (com as ações já decididas) e só melhora a forma,
respondendo ao que o cliente escreveu. Checagens determinísticas protegem contra o risco
real do LLM aqui — prometer o que não foi decidido ou omitir um assunto:

1. sem dado pessoal (CPF, cartão, telefone);
2. cada ação decidida continua mencionada (palavras-chave obrigatórias);
3. nenhuma ação NÃO decidida é prometida (palavras proibidas);
4. valores e prazos do template preservados;
5. tamanho razoável.
Se qualquer checagem falhar, devolve o template e registra o motivo.
"""
import re

from langchain_core.messages import HumanMessage, SystemMessage

from atendimento.dominio.schemas import Decisao
from atendimento.servicos.llm import criar_chat, eh_rate_limit, espera_sugerida, medir_uso

MODELO_REDACAO = "openai/gpt-oss-120b"

PROMPT = """Você é redator do atendimento da {marca} (e-commerce de beleza/acessórios).
Reescreva o RASCUNHO abaixo como uma resposta calorosa, clara e breve ao cliente, em português do Brasil.

Regras obrigatórias:
- Mantenha TODAS as informações do rascunho: cada ação, valor, prazo e item solicitado.
- NÃO prometa nada que não esteja no rascunho (nenhum reembolso, estorno, reenvio, troca, cupom ou prazo novo).
- Reconheça brevemente o que o cliente relatou, sem repetir dados pessoais.
- Um parágrafo por assunto. No máximo 120 palavras. Termine com "Equipe {marca}".
- Responda só com o texto final, sem comentários."""

# tipo de ação → termos que precisam aparecer (qualquer um da lista)
OBRIGATORIOS = {
    "estorno": ["estorno", "estornad", "devolu"],
    "reembolso_integral": ["reembolso", "reembols"],
    "reenvio_sem_custo": ["reenvi", "enviar novamente", "enviaremos novamente", "novo envio"],
    "nova_producao": ["nova peça", "produzir", "nova produção", "produção"],
    "abrir_chamado_transportadora": ["transportadora"],
    "informar_status": ["trânsito", "transito", "separação", "entregue", "pagamento", "atraso"],
    "solicitar_informacoes": ["envie", "enviar", "mande", "mandar", "compartilhe", "informe"],
    "informar_inelegibilidade": ["não é possível", "não é mais possível", "infelizmente", "não conseguimos"],
    "alterar_endereco": ["endereço"],
    "agradecer": ["obrigad", "agradec", "feliz"],
}
# promessas que só podem aparecer se a ação correspondente foi decidida
PROMESSAS = {
    "estorno": r"\bestorn", "reembolso_integral": r"\breembols", "reenvio_sem_custo": r"\breenvi",
    "nova_producao": r"nova produ|produzir uma nova", "troca_fragrancia": r"\btroca(r)?\b",
}
RE_PII = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}|\d{4}[ .-]?\d{4}[ .-]?\d{4}[ .-]?\d{4}|\(?\d{2}\)?\s?9?\d{4}-\d{4}")


def checar(texto: str, template: str, decisao: Decisao) -> list[str]:
    problemas, baixo = [], texto.lower()
    if RE_PII.search(texto):
        problemas.append("contém dado pessoal")
    tipos = {a.tipo for a in decisao.acoes}
    for tipo in tipos:
        if tipo in OBRIGATORIOS and not any(k in baixo for k in OBRIGATORIOS[tipo]):
            problemas.append(f"omitiu a ação '{tipo}'")
    # permitido citar: ações decididas + ações condicionadas a receber a informação pedida
    permitidos = tipos | {a.parametros.get("acao_se_confirmado") for a in decisao.acoes}
    alternativas_reenvio = "informar_inelegibilidade" in tipos  # template de endereço cita reenvio como alternativa
    for tipo, padrao in PROMESSAS.items():
        if tipo not in permitidos and re.search(padrao, baixo) and not (tipo == "reenvio_sem_custo" and alternativas_reenvio):
            problemas.append(f"prometeu '{tipo}' sem decisão")
    # valores (R$ 97,69) e prazos (48 horas, 5 dias úteis, 2 faturas): o NÚMERO precisa sobreviver
    for numero in re.findall(r"R\$ ?(\d[\d.]*,\d{2})|(\d+) (?:dias úteis|horas|faturas)", template):
        valor = next(n for n in numero if n)
        if valor not in texto:
            problemas.append(f"perdeu o valor/prazo '{valor}'")
    if len(texto.split()) > 180:
        problemas.append("texto longo demais")
    return problemas


def reescrever(template: str, decisao: Decisao, mensagens_cliente: list[str], marca: str,
               modelo: str = MODELO_REDACAO) -> tuple[str, str]:
    """Devolve (texto, origem). origem: 'llm' ou 'template (motivo da recusa)'."""
    import time
    marca = marca or "Gocase"
    chat = criar_chat(modelo, temperatura=0.3)
    msgs = [SystemMessage(PROMPT.format(marca=marca)),
            HumanMessage("MENSAGENS DO CLIENTE:\n" + "\n".join(mensagens_cliente) + f"\n\nRASCUNHO:\n{template}")]
    for _ in range(6):
        try:
            with medir_uso("redacao"):
                texto = chat.invoke(msgs).content.strip()
            break
        except Exception as e:
            if not eh_rate_limit(e) or espera_sugerida(e) > 120:
                return template, f"template (erro LLM: {type(e).__name__})"
            time.sleep(espera_sugerida(e))
    else:
        return template, "template (rate limit)"
    problemas = checar(texto, template, decisao)
    return (texto, "llm") if not problemas else (template, "template (" + "; ".join(problemas) + ")")
