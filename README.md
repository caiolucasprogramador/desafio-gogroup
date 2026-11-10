# Agente de Atendimento: Desafio AI-First Gogroup

Um agente de IA que lê a mensagem do cliente, identifica **todos** os motivos do contato, cruza com o
pedido, prioriza, confere as políticas e decide: **resolve sozinho** (com a resposta pronta) ou
**encaminha a uma pessoa** (com um dossiê do caso). Junto com ele, um diagnóstico do histórico de
atendimento que responde, com números, às perguntas do Problema 1.

- **Solução publicada (sem login):** `TODO: link da Vercel`
  - *Diagnóstico*: as 4 respostas abaixo, com gráficos (`/diagnostico.html`)
  - *Testar o agente*: digite uma mensagem, simule o pedido e veja cada etapa da decisão (`/`)
- **Repositório:** https://github.com/caiolucasprogramador/desafio-gogroup

## O problema

> *A liderança não tem uma visão confiável de por que os clientes nos procuram, nem do que fazer a respeito.*

A única visão disponível é a `tag_agente`, preenchida à mão ao encerrar a conversa: uma tag por
conversa, mesmo quando o cliente traz dois assuntos. No gabarito de 96 conversas, essa tag aponta o
motivo principal em **53,2%** dos casos; o agente acerta **94,8%**. Ou seja, qualquer decisão tomada
hoje a partir das tags parte de um retrato errado em quase metade das conversas.

## As respostas, com números

Base: 4.000 conversas de 02/07 a 29/09/2026 (90 dias, 9 marcas), que são **uma amostra de 1 em cada 3
clientes**. Por isso as contagens são da amostra e os **custos são trimestrais da operação inteira**
(custo da amostra × 3, ≈ 12.000 conversas). Custo por conversa: WhatsApp R$ 4,80, e-mail R$ 7,20,
Reclame Aqui R$ 42,00. Os percentuais não dependem da expansão.

**Custo trimestral estimado do atendimento: R$ 108.299.**

### 1. Por que os clientes nos procuram, e qual o peso real de cada motivo?

O peso real é o **custo**, não o volume: o mesmo motivo custa 9× mais quando chega pelo Reclame Aqui.

| Canal | % das conversas | % do custo | Custo trimestral |
|---|---:|---:|---:|
| Reclame Aqui | 10% | **47%** | R$ 51.282 |
| WhatsApp | 72% | 38% | R$ 41.184 |
| E-mail | 18% | 15% | R$ 15.833 |

| Categoria (motivo principal) | % das conversas | % do custo | Custo trimestral |
|---|---:|---:|---:|
| Entrega | 36,0% | 38,4% | R$ 41.576 |
| Pedido incompleto ou danificado | 21,9% | 21,2% | R$ 22.997 |
| Financeiro | 7,8% | **11,0%** | R$ 11.884 |
| Cancelamento e troca | 10,2% | 10,9% | R$ 11.794 |
| Produto | 7,5% | 7,4% | R$ 8.046 |
| Outros (inclui abandono no bot) | 12,4% | 7,1% | R$ 7.654 |
| Promoção e cupom | 2,4% | 2,3% | R$ 2.516 |
| Saúde | 1,6% | 1,7% | R$ 1.832 |

- **Atraso na entrega** é o motivo mais caro: R$ 23.738 (18% das conversas, 22% do custo), seguido de
  **dúvida de rastreio** (R$ 14.227) e **avaria ou vazamento** (R$ 8.546).
- **Financeiro** pesa mais no custo do que no volume (7,8% das conversas, 11% do custo): 20% dessas
  conversas chegam pelo Reclame Aqui, o dobro da média. Cobrança duplicada sozinha é 4% das conversas e 6,6% do custo.
- **Abandono no bot** é o inverso: 11,5% das conversas e 6,1% do custo (é todo WhatsApp, o canal mais barato).

Cada conversa tem um motivo principal (o de maior gravidade; empate → o primeiro citado) e o custo
dela vai inteiro para esse motivo. Assim as linhas somam o total, sem dupla contagem.

### 2. Quais contatos poderiam simplesmente não existir?

**R$ 48.902 por trimestre (45% do custo)**, sem contar duas vezes a conversa que cai em mais de um item:

| Contato | Conversas (amostra) | Custo trimestral | Como evitar |
|---|---:|---:|---|
| Cliente voltando a perguntar (recontato) | 739 (18%) | R$ 28.642 | Responder o primeiro contato por completo, com todos os assuntos; avisar quando houver novidade |
| Dúvida de rastreio | 581 | R$ 14.227 | Aviso proativo de status e link de rastreio na confirmação do pedido |
| Abandono no bot | 459 | R$ 6.610 | Menu do bot guiado por motivo, com resposta para os casos simples |
| Alteração de endereço | 136 | R$ 3.611 | Autoatendimento no site enquanto o pedido não foi separado |

O recontato é o maior item. O agente ataca essa causa: identifica **todos** os motivos da mensagem e
responde a todos de uma vez, em vez de tratar só um assunto por conversa.

### 3. O que o time deveria atacar primeiro, e com que critério?

**Critério:** custo trimestral × gravidade × facilidade de ação. Primeiro o que concentra custo e tem
ação clara; saúde entra pela gravidade, não pelo custo.

1. **Reclame Aqui** (407 conversas, R$ 51.282): 10% dos contatos e 47% do custo; cada caso custa 9× um
   WhatsApp e a resposta é pública. Resolver antes de o cliente chegar lá vale mais que qualquer outra ação.
2. **Atraso e rastreio** (1.306 conversas, R$ 37.966): o maior volume (33% dos contatos). A dúvida de
   rastreio some com aviso proativo; o atraso vira chamado automático na transportadora.
3. **Recontato** (739 conversas, R$ 28.642): contatos que só existem porque o primeiro não resolveu.
4. **Saúde** (65 conversas, R$ 1.832): poucos casos, mas risco ao cliente e prazo de 24h de
   cosmetovigilância. Fura a fila e vai sempre para a responsável técnica.

Dentro da fila, o agente ordena cada conversa por um score: gravidade 40%, canal 15%, SLA consumido 15%,
recontato 15%, valor do pedido 10% e tom 5%.

### 4. Que ações o sistema pode tomar sozinho, e quais precisam de uma pessoa?

Rodando o agente na fila real (1.337 conversas pendentes ou reabertas):

- **784 (59%) automáticas** e **553 (41%) para uma pessoa**.
- Das automáticas, 222 têm como ação principal pedir uma informação ao cliente (foto, número do
  pedido…). A **resolução completa**, sem nenhuma pessoa, fica em **42%** da fila.

| Ação automática (principal) | Conversas |
|---|---:|
| Pedir informação ao cliente | 222 |
| Abrir chamado na transportadora | 219 |
| Informar status do pedido | 180 |
| Reembolso integral (arrependimento, até R$ 200) | 66 |
| Explicar que a política não cobre | 43 |
| Estorno de cobrança duplicada | 36 |
| Agradecer elogio | 15 |
| Nova produção da personalização | 3 |

| Fila humana | Conversas |
|---|---:|
| Atendimento | 170 |
| Reclame Aqui (sempre humano: resposta pública) | 157 |
| Comercial | 137 |
| Financeiro | 43 |
| Responsável técnica (saúde: sempre humano) | 27 |
| Logística | 19 |

**O que destravaria mais automação são políticas, não tecnologia.** Conversas que hoje vão para uma
pessoa **só** porque um motivo não tem regra escrita, e virariam automáticas com ela:

| Motivo sem política | Conversas | Sugestão |
|---|---:|---|
| Brinde faltante | 88 | Política de reenvio do brinde (ou cupom equivalente) |
| Dúvida sobre produto | 85 | Base de conhecimento de produtos para o agente consultar |
| Insatisfação com o produto | 53 | Troca ou cupom por insatisfação, como a de fragrância |
| Troca (exceto fragrância) | 28 | Política geral de troca, com prazo e condições |
| Pagamento não confirmado | 24 | Consulta automática da baixa no gateway |
| Cupom não aplicado | 22 | Regras de cupons acessíveis ao agente |
| Cashback | 15 | Regras e saldo de cashback acessíveis ao agente |
| Frete grátis não aplicado | 6 | Regra de frete grátis acessível ao agente |

Juntas, até **321 conversas (24% da fila)** sairiam da fila humana.

## Como o agente funciona

Um grafo [LangGraph](https://langchain-ai.github.io/langgraph/) com nós finos que chamam serviços:

```
START → anonimizar → classificar ─┬─(sem conteúdo)→ END
                                  └→ enriquecer → priorizar → checar_elegibilidade → regras_fixas
regras_fixas ─┬─(saúde / Reclame Aqui)→ escalar_humano → END
              └→ decidir ─┬─(todos os motivos automáticos)→ agir → END
                          └─(algum motivo exige pessoa)→ escalar_humano → END
```

| Nó | O que faz | LLM? |
|---|---|---|
| `anonimizar` | Mascara CPF, cartão, telefone e e-mail **antes** de qualquer LLM | não |
| `classificar` | Todos os motivos (25 motivos em 8 categorias), recontato e tom, com o trecho que comprova cada motivo | **sim** (`gemini-3.5-flash-lite`) |
| `enriquecer` | Cruza com o pedido: status de entrega, valor, dias desde a compra, contatos anteriores | não |
| `priorizar` | Score 0–100 com os pesos acima; saúde vai para o topo | não |
| `checar_elegibilidade` | Cada motivo contra a política vigente: elegível, inelegível ou **indeterminado** (e o que falta perguntar) | não |
| `regras_fixas` | Saúde e Reclame Aqui sempre vão para uma pessoa | não |
| `decidir` | Tabela determinística motivo → ação. Motivo sem regra vai para uma pessoa. A conversa só é automática se **todos** os motivos forem | não |
| `agir` | Executa (simulado) e escreve a resposta a partir de templates; opcionalmente reescreve o tom com LLM | opcional |
| `escalar_humano` | Dossiê para a fila certa: motivos, evidências, pedido, ações sugeridas | não |

**Princípio: dinheiro e decisão são regra, nunca LLM.** O LLM só classifica e, se ligado, melhora o
tom da resposta. A reescrita passa por checagens determinísticas (nenhum dado pessoal, toda ação
decidida mencionada, nenhuma ação não decidida prometida, valores e prazos preservados) e, se falhar
em qualquer uma, a resposta volta a ser o template. Reembolso, estorno e reenvio acima de R$ 200 vão
para revisão humana.

## Como os números foram calculados

- **Classificação:** as 4.000 conversas foram classificadas em lote pelo mesmo classificador do agente
  (`atendimento/lote.py`, com cache e deduplicação de textos para caber na cota gratuita).
- **Avaliação:** gabarito de 96 conversas, amostra estratificada: 5 por tag manual (inclusive sem tag),
  mais casos raros que importam (saúde, cobrança duplicada, vários assuntos na mesma mensagem) e 2
  abandonos no bot, para que o gabarito não fosse dominado por rastreio. Motivo principal 94,8% (agente) × 53,2% (tag manual), na mesma régua; recall dos
  motivos 98,3%; saúde detectada em 14 de 14. Se a tag "acertar" quando bate com *qualquer* motivo da
  conversa, ela chega a 60,6%.
- **Fila:** o grafo completo rodou nas 1.337 conversas pendentes ou reabertas, sem LLM (classificação
  do cache, resto determinístico).
- **Diagnóstico:** `scripts/gerar_diagnostico.py` gera `public/diagnostico.json` só com agregados e se
  recusa a gravar se encontrar ID do case, dado pessoal ou qualquer sequência de 6 palavras copiada de
  uma mensagem. `tests/test_diagnostico.py` valida o formato e a privacidade do arquivo publicado.

## Limitações

- **O gabarito foi rotulado por IA**, sem validação humana. Os 94,8% medem a concordância com esse
  gabarito, não com um atendente experiente.
- **Não há data de recebimento** nos dados. Para prazos contados do recebimento, o agente usa um
  limite seguro (recebido há no máximo os dias desde o pedido) e, quando não dá para ter certeza,
  pergunta ao cliente em vez de decidir.
- O SLA ignora o horário comercial (8h às 20h).
- Os pesos da prioridade são julgamento, não calibrados com dados de resultado.
- O limite de R$ 200 para ação automática com custo cobre cerca de 95% dos pedidos e ainda está pendente de confirmação.
- As ações são **simuladas**: não há integração com transportadora, gateway ou ERP.
- Os LLMs usam cotas gratuitas (Gemini e Groq). No link público, o volume de testes é limitado por
  um limitador de requisições.

## Dados e privacidade

O enunciado proíbe compartilhar o case. Por isso **nenhum dado do case está neste repositório nem
no site**: os CSVs, o PDF e tudo o que é derivado deles (`case_*/`, `dados/`) ficam fora do git e do
deploy. O que é publicado:

- `public/diagnostico.json`: só agregados (contagens, custos, percentuais), sem IDs nem textos;
- a tela *Testar o agente*: usa a mensagem que você digita e um **pedido simulado**; os exemplos
  prontos foram escritos à mão.

Sem os dados do case, os testes rodam normalmente; só os que leem `dados/` ficam pulados.

## Como rodar

Requer Python 3.12+.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # GEMINI_API_KEY (classificação) e, opcional, GROQ_API_KEY (reescrita do tom)

uvicorn main:app --reload        # http://localhost:8000 (Testar o agente) e /diagnostico.html
python -m pytest -q              # testes, sem LLM
```

Com os dados do case em `case_atendimento/` e `dados/`:

```bash
SEM_LLM=1 python -m scripts.processar_fila    # grafo na fila real → dados/resultados_grafo.jsonl
python -m scripts.gerar_diagnostico           # agregados → public/diagnostico.json
```

`SEM_LLM=1` bloqueia qualquer chamada a LLM (usa só o cache de classificação).

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `atendimento/dominio/` | Taxonomia (motivos, gravidade), políticas, parâmetros, rótulos, schemas Pydantic |
| `atendimento/servicos/` | Uma regra por etapa: anonimização, classificação, enriquecimento, priorização, elegibilidade, decisão, respostas, redação |
| `atendimento/grafo/` | Estado, fluxo, roteamento e nós do LangGraph |
| `atendimento/api/` | FastAPI: `POST /api/atender`, `GET /api/exemplos`, `GET /api/opcoes` |
| `public/` | Páginas estáticas (HTML + JS, sem build) e `diagnostico.json` |
| `scripts/` | Classificação em lote, avaliação, fila, diagnóstico |
| `tests/` | pytest, sem LLM |
| `main.py` | Ponto de entrada da Vercel |
