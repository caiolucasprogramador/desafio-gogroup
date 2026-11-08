"""Classificação em lote das conversas históricas, respeitando o plano gratuito da Groq.

Estratégia (plano gratuito: limites por minuto E por dia, por modelo):
1. Normaliza o texto (pedido, data e dados pessoais não mudam o motivo) e deduplica.
2. Agrupa N textos únicos por requisição: o prompt da taxonomia é pago uma vez por grupo.
3. reasoning_effort="low" reduz tokens de raciocínio.
4. Cache em disco (JSONL): pode ser interrompido e retomado sem perder nada.
"""
import hashlib
import json
import re
import time
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from atendimento.servicos.anonimizacao import anonimizar
from atendimento.servicos.classificacao import MODELO_PADRAO, PROMPT_SISTEMA, finalizar
from atendimento.servicos.llm import (
    criar_estruturado, eh_cota_diaria, eh_rate_limit, eh_transitorio, espera_sugerida, medir_uso,
)
from atendimento.dominio.schemas import Classificacao, ClassificacaoLLM

VERSAO_PROMPT = hashlib.sha1(PROMPT_SISTEMA.encode()).hexdigest()[:8]


def normalizar(mensagens_cliente: list[str]) -> str:
    """Chave de deduplicação: remove o que não muda o motivo do contato."""
    partes = []
    for t in mensagens_cliente:
        t = anonimizar(t)
        t = re.sub(r"\bG[BC]\d+\b", "[PEDIDO]", t)
        t = re.sub(r"\b\d{1,2}/\d{1,2}\b", "[DATA]", t)
        t = re.sub(r"\s*(Meu CPF é|O cartão cobrado foi o|Me liga no)?\s*\[(CPF|CARTAO|TELEFONE|EMAIL)\]", "", t)
        partes.append(t.strip())
    return "\n".join(f"Cliente: {p}" for p in partes)


class CotaDiariaEsgotada(Exception):
    """Limite diário de tokens do modelo: não adianta esperar segundos, interrompe o lote."""


class ItemLote(ClassificacaoLLM):
    id: int = Field(description="Número da conversa, igual ao informado na entrada.")


class SaidaLote(BaseModel):
    itens: list[ItemLote] = Field(description="Uma classificação para CADA conversa da entrada.")


INSTRUCAO_LOTE = (
    "\n\nVocê receberá várias conversas numeradas (### Conversa N). "
    "Classifique cada uma de forma independente e devolva exatamente um item por conversa, com o mesmo id."
)


class ClassificadorLote:
    def __init__(self, cache: Path, modelo: str = MODELO_PADRAO, tamanho_grupo: int = 15, rpm: int = 12):
        """rpm: teto de requisições/minuto (abaixo do limite do plano, ex.: 15 no Gemini Flash Lite)."""
        self.cache, self.modelo, self.tamanho_grupo = cache, modelo, tamanho_grupo
        self.intervalo_minimo, self._ultima_chamada = 60 / rpm, 0.0
        self._clf = None  # criado só na 1ª chamada: ler o cache não exige chave de API
        self.memoria: dict[str, dict] = {}
        if cache.exists():
            for linha in cache.read_text(encoding="utf-8").splitlines():
                reg = json.loads(linha)
                if reg["versao"] == VERSAO_PROMPT and reg["modelo"] == modelo:
                    self.memoria[reg["chave"]] = reg["saida"]

    @property
    def clf(self):
        if self._clf is None:
            self._clf = criar_estruturado(self.modelo, SaidaLote)
        return self._clf

    def _chamar(self, textos: list[str]) -> dict[int, ClassificacaoLLM]:
        """Uma requisição. Repete sozinha em rate limit (429) e falha transitória (503)."""
        entrada = "\n\n".join(f"### Conversa {i}\n{t}" for i, t in enumerate(textos))
        msgs = [SystemMessage(PROMPT_SISTEMA + INSTRUCAO_LOTE), HumanMessage(entrada)]
        for tentativa in range(8):
            if (falta := self.intervalo_minimo - (time.time() - self._ultima_chamada)) > 0:
                time.sleep(falta)  # espaçamento: evita o 429 em vez de reagir a ele
            self._ultima_chamada = time.time()
            try:
                with medir_uso("classificacao_lote"):
                    saida: SaidaLote = self.clf.invoke(msgs)
                return {it.id: ClassificacaoLLM(**it.model_dump(exclude={"id"})) for it in saida.itens}
            except Exception as e:
                if eh_rate_limit(e):
                    espera = espera_sugerida(e)
                    if eh_cota_diaria(e) or espera > 300:
                        raise CotaDiariaEsgotada(str(e)) from e
                    motivo = "rate limit"
                elif eh_transitorio(e):
                    espera, motivo = min(10 * 2 ** tentativa, 120), "servidor indisponível"
                else:
                    raise  # saída inválida ou erro de configuração: quem chamou decide
                print(f"  {motivo}, aguardando {espera:.0f}s")
                time.sleep(espera)
        raise RuntimeError("falhas transitórias persistentes")

    def classificar_unicos(self, chaves: list[str]) -> None:
        pendentes = [c for c in dict.fromkeys(chaves) if c not in self.memoria]
        print(f"{len(set(chaves))} textos únicos | {len(pendentes)} fora do cache")
        fila: list[list[str]] = [pendentes[i:i + self.tamanho_grupo]
                                 for i in range(0, len(pendentes), self.tamanho_grupo)]
        with self.cache.open("a", encoding="utf-8") as f:
            while fila:
                grupo = fila.pop(0)
                t0 = time.time()
                try:
                    res = self._chamar(grupo)
                except CotaDiariaEsgotada:
                    print(f"  cota diária esgotada; {sum(map(len, fila)) + len(grupo)} textos ficam para depois")
                    return
                except Exception as e:
                    if any(k in str(e) for k in ("NOT_FOUND", "PERMISSION_DENIED", "API key", "401", "403")):
                        raise  # erro de configuração: insistir não resolve
                    print(f"  saída inválida em grupo de {len(grupo)} ({type(e).__name__}: {str(e)[:100]})")
                    if len(grupo) > 1:  # divide SÓ este grupo; os demais seguem no tamanho normal
                        meio = len(grupo) // 2
                        fila[:0] = [grupo[:meio], grupo[meio:]]
                    continue
                for i, chave in enumerate(grupo):
                    if i in res:
                        saida = res[i].model_dump()
                        self.memoria[chave] = saida
                        f.write(json.dumps({"chave": chave, "versao": VERSAO_PROMPT,
                                            "modelo": self.modelo, "saida": saida}, ensure_ascii=False) + "\n")
                f.flush()
                if faltando := [c for i, c in enumerate(grupo) if i not in res]:
                    fila.append(faltando)  # o modelo pulou itens: tenta de novo no fim
                restantes = sum(map(len, fila))
                print(f"  +{len(res)} ({len(self.memoria)} em cache, {restantes} restantes) {time.time() - t0:.0f}s")

    def resultado(self, mensagens_cliente: list[str]) -> Classificacao | None:
        from atendimento.servicos.classificacao import classificacao_sem_conteudo
        if not mensagens_cliente:
            return classificacao_sem_conteudo()
        saida = self.memoria.get(normalizar(mensagens_cliente))
        return finalizar(ClassificacaoLLM(**saida), self.modelo) if saida else None
