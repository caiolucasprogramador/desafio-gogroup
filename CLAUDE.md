# Agente de Atendimento — Desafio AI-First Gogroup

Processo seletivo da Gogroup (etapa 3), **Problema 1: Atendimento**. O entregável é um agente de IA
que executa uma ação útil, **publicado num link público sem login**, com o código num **repositório
público**, e com as respostas do enunciado **defendidas com números**.

O agente lê a mensagem do cliente, classifica os motivos, cruza com o pedido, prioriza, confere as
políticas e decide: **resolve sozinho** (com a resposta pronta) ou **encaminha a um humano** (com o dossiê).

Dono do projeto: Caio. Ele aprende fazendo: explique o porquê das mudanças, em português, de forma didática.

## Regras inegociáveis

1. **Dados do case são confidenciais.** O enunciado proíbe compartilhar o PDF e os dados.
   `case_*/`, `*.pdf`, `dados/` e `.env` ficam fora do git (`.gitignore`) e do deploy (`.vercelignore`).
   Nunca commite, publique, cole em artefato público ou envie para serviço externo nenhum texto de
   conversa, pedido ou cliente do case. Números **agregados** podem ir para o README.
2. **Segredos só no `.env`** (`GEMINI_API_KEY`, `GROQ_API_KEY`). Nunca peça para colar chave no chat.
   Na Vercel, as chaves são variáveis de ambiente do projeto.
3. **Anonimizar antes de qualquer LLM** (CPF, cartão, telefone, e-mail): é o primeiro nó do grafo.
4. **Saúde (`reacao_adversa`, `duvida_saude`) e Reclame Aqui sempre vão para humano.**
5. **Dinheiro e decisão são regra, nunca LLM.** O LLM só classifica e, opcionalmente, reescreve o tom
   da resposta (com checagens que devolvem o template se ele prometer algo não decidido).
6. **Commit e push só quando o Caio pedir.** Em geral ele mesmo commita: entregue os comandos prontos
   (padrão Conventional Commits em português, sem acento: `feat(api): ...`).
7. **Uso de LLM consome cota gratuita.** Não rode lotes ou avaliações com LLM sem combinar antes.
   Para testar sem LLM: `SEM_LLM=1`.

## Arquitetura

Grafo LangGraph (`atendimento/grafo/fluxo.py`), nós finos que chamam serviços:

```
START → anonimizar → classificar ─┬─(sem_conteudo)→ END
                                  └→ enriquecer → priorizar → checar_elegibilidade → regras_fixas
regras_fixas ─┬─(saúde / Reclame Aqui)→ escalar_humano → END
              └→ decidir ─┬─(todos os motivos automáticos)→ agir → END
                          └─(algum motivo exige humano)→ escalar_humano → END
```

| Pasta | Conteúdo |
|---|---|
| `atendimento/dominio/` | taxonomia (8 categorias, 26 motivos, `GRAVIDADE`), políticas, parâmetros, schemas Pydantic |
| `atendimento/servicos/` | regras de cada etapa: anonimização, classificação (LLM), enriquecimento, priorização, elegibilidade, decisão, respostas (templates), redação (LLM opcional), cliente LLM |
| `atendimento/grafo/` | estado, fluxo, roteamento e nós |
| `atendimento/lote.py` | classificação em lote com cache JSONL (histórico de 4.000 conversas já classificado) |
| `atendimento/api/` | FastAPI: `POST /api/atender`, `GET /api/exemplos`, `GET /api/opcoes`, limitador de requisições |
| `public/index.html` | tela "Testar o agente" (HTML + JS puros, sem build) |
| `main.py` | ponto de entrada da Vercel (reexporta o app) |
| `scripts/` | lote, avaliação, fila priorizada, processamento da fila, amostra de redação |
| `tests/` | pytest sem LLM e sem CSV |

**Modo demonstração (o que está publicado):** a API recebe a mensagem digitada + um **pedido
simulado** (`pedido_simulado` no estado). O nó `enriquecer` monta o contexto a partir dele, sem ler
os CSVs. Por isso a API publicada não expõe nenhum dado do case e não depende do pandas.

## Decisões já tomadas (não rediscutir sem o Caio)

- Motivo principal = o de maior `GRAVIDADE`; empate → o primeiro mencionado.
- Prioridade = média ponderada: gravidade 40%, canal 15%, SLA 15%, recontato 15%, valor 10%, tom 5%. Saúde fura a fila.
- `decidir` é uma tabela determinística; motivo sem regra vai para humano. A conversa só é automática se **todos** os motivos forem.
- O nó `auditar` foi removido; suas garantias viraram `tests/test_invariantes.py`.
- Classificação: `gemini-3.5-flash-lite` (Groq tem limite diário baixo). Redação opcional: `openai/gpt-oss-120b` (Groq).
- Publicar **só** a tela "Testar o agente" com pedido simulado; nenhuma fila ou conversa real no link.
- Hospedagem: **Vercel** (a GoCase usa Vercel).
- Pendente de confirmação do Caio: limite de **R$ 200** para ação automática com custo (`LIMITE_VALOR_AUTOMATICO`).

## Comandos

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt        # local: produção + pandas + pytest + httpx

uvicorn main:app --reload                  # http://localhost:8000
python -m pytest -q                        # testes (sem LLM)
SEM_LLM=1 python -m scripts.processar_fila # grafo na fila real → dados/resultados_grafo.jsonl
SEM_LLM=1 python -m scripts.rodar_grafo <conversation_id> ...
```

`tests/test_invariantes.py` só roda se `dados/resultados_grafo.jsonl` existir (fica pulado em máquinas sem os dados).

## Deploy (Vercel)

- Deploy automático a cada push na `main`.
- `requirements.txt` = **só produção**. Limite da função: 250 MB (hoje ~132 MB). **Não adicione pandas,
  numpy ou pytest nele**; dependências de desenvolvimento vão no `requirements-dev.txt`.
- O disco é somente leitura: nada pode gravar arquivo no caminho da API (o registro de tokens em
  `servicos/llm.py` já ignora a falha).
- O limitador de requisições (`api/limite.py`) é em memória: na Vercel ele vale por instância, não globalmente.
- Antes de mexer no deploy, simule: Python 3.12 + só `requirements.txt` + só os arquivos fora do `.vercelignore`.

## Números para o README (agregados, podem ser publicados)

- Classificação no gabarito de 96 conversas: motivo principal **94,8%** (contra **59,5%** da tag manual), recall 98,3%, saúde 14/14.
  Limitação: o gabarito foi rotulado por IA, sem validação humana.
- Fila pendente/reaberta: 1.337 conversas; **59% automatizáveis** (784) e 41% para humano (553).
  Dos automáticos, 222 apenas pedem informação: a resolução completa fica em torno de 42%.
- Custo trimestral estimado: **R$ 108.299**. Reclame Aqui = 10% das conversas e **47% do custo** (R$ 51.282).
- Para humano por falta de política (oportunidades): brinde faltante 92, dúvida de produto 86,
  insatisfação 53, troca (exceto fragrância) 31.
- Outras limitações: sem data de recebimento (usamos um limite seguro), SLA ignora horário comercial,
  pesos não calibrados com dados, cotas gratuitas de LLM.

## Backlog

1. **Frontend mais agradável** (`public/index.html`): carregamento com os nós acendendo, introdução
   curta do que o avaliador está vendo, link para o repositório, comparação template × LLM lado a lado.
   Manter: tema claro/escuro, funcionar no celular, escapar todo texto vindo da API (sem `innerHTML`).
2. **README** com problema, arquitetura, números acima, limitações, como rodar e o link público.
3. Fazer a resposta do Reclame Aqui passar pelo `decidir` antes de ir para humano (o dossiê ganharia ações sugeridas).
