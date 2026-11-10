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
| `atendimento/dominio/` | taxonomia (8 categorias, 25 motivos, `GRAVIDADE`), políticas, parâmetros, schemas Pydantic |
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
- No link público, nenhuma fila ou conversa real: a tela "Testar o agente" usa pedido simulado.
  Números **agregados** (página Diagnóstico) estão no plano, aguardando confirmação do Caio.
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

Fonte única: `public/diagnostico.json`, gerado por `scripts/gerar_diagnostico.py` (que confere os
números abaixo a cada execução e marca ✗ o que mudar). Se um número mudar, atualize aqui e no README.

- **Escala:** os arquivos são uma amostra de 1 em cada 3 clientes. Contagens de conversas são da
  amostra (4.000); custos são trimestrais da operação inteira (amostra × 3, ≈ 12.000 conversas).
- Classificação no gabarito de 96 conversas: motivo principal **94,8%** contra **53,2%** da tag manual
  (mesma régua: o motivo principal do gabarito; se a tag puder bater com qualquer motivo, 60,6%),
  recall 98,3%, saúde 14/14. Limitação: o gabarito foi rotulado por IA, sem validação humana.
  (O antigo 59,5% era de uma rodada anterior, com 79 conversas e outro critério de motivo principal.)
- Custo trimestral estimado: **R$ 108.299**. Reclame Aqui = 10% das conversas e **47% do custo** (R$ 51.282).
  Entrega (categoria) R$ 41.576; atraso R$ 23.738; rastreio R$ 14.227.
- Contatos evitáveis: recontato R$ 28.642 (739 conversas), rastreio R$ 14.227, abandono no bot R$ 6.610,
  endereço R$ 3.611; total sem dupla contagem **R$ 48.902** (45% do custo).
- Fila pendente/reaberta: 1.337 conversas; **59% automatizáveis** (784) e 41% para humano (553).
  Dos automáticos, 222 têm como ação principal pedir informação: a resolução completa fica em 42%.
- Políticas faltantes = conversas humanas cujo **único** bloqueio é esse motivo (virariam automáticas
  com a política): brinde faltante 88, dúvida de produto 85, insatisfação 53, troca (exceto fragrância) 28,
  pagamento não confirmado 24, cupom 22, cashback 15, frete grátis 6.
- Outras limitações: sem data de recebimento (usamos um limite seguro), SLA ignora horário comercial,
  pesos não calibrados com dados, cotas gratuitas de LLM.

## Plano de implementação (o que falta)

O enunciado pede só **dois links** (solução publicada + repositório público) e diz que as melhores
respostas são **defendidas com números**. Não há relatório à parte: os números precisam estar
**dentro da solução**. Contexto do Problema 1: *"A liderança não tem uma visão confiável de por que
os clientes nos procuram, nem do que fazer a respeito."*

### Situação dos requisitos

| Requisito | Situação |
|---|---|
| Agente de IA com ação útil | ✅ classifica, decide e responde ou encaminha com dossiê |
| Link público sem login | ✅ publicado na Vercel (confirmar que o "Atender" funciona lá com as chaves) |
| Repositório público no GitHub | ❌ ainda privado |
| Respostas com números | 🟡 `public/diagnostico.json` (agregados reais) e README prontos; falta a página Diagnóstico |

### Perguntas de referência do enunciado → nossa resposta (já calculada)

| Pergunta | Resposta |
|---|---|
| Por que os clientes nos procuram, e qual o peso real de cada motivo? | motivo × volume × custo nas 4.000 conversas; custo trimestral R$ 108 mil; tag manual acerta 53,2% contra 94,8% do agente |
| Quais contatos poderiam simplesmente não existir? | recontato (R$ 28,6 mil), dúvida de rastreio (R$ 14,2 mil), abandono no bot (R$ 6,6 mil), endereço (R$ 3,6 mil); R$ 48,9 mil sem dupla contagem |
| O que o time deveria atacar primeiro, e com que critério? | Reclame Aqui (10% dos contatos, 47% do custo) → atraso e rastreio → recontato → saúde (pela gravidade) |
| Que ações o sistema pode tomar sozinho, e quais precisam de uma pessoa? | 59% automatizável / 41% humano, por motivo, e as políticas que faltam para destravar o resto |

### Tarefas, em ordem

1. **Página "Diagnóstico" no site** (prioridade máxima).
   - Script em `scripts/` que lê os dados locais e gera um JSON **só com agregados** (totais e
     percentuais por motivo, canal, custo, automático × humano). Nenhum texto de conversa, nenhum
     ID de cliente, pedido ou conversa. Esse JSON é versionado e servido com a página.
   - Página que lê o JSON e responde às 4 perguntas acima com números e gráficos.
   - Navegação entre "Diagnóstico" e "Testar o agente".
   - Antes de publicar: confirmar com o Caio que os agregados podem ir para o site (ele havia
     decidido publicar só a tela do agente para não expor conversas; agregados não expõem nenhuma).
2. **README**: o problema, as respostas às 4 perguntas com os mesmos números, arquitetura,
   limitações, como rodar e os dois links.
3. **Repositório público**: antes, o Caio decide se `scripts/rotulos_propostos.py` fica (contém só
   IDs de conversa e rótulos do gabarito, sem texto; sugestão: manter e explicar no README).
   Depois: GitHub → Settings → Change visibility → Public.
4. **Frontend mais agradável** (`public/index.html`): carregamento com os nós acendendo, introdução
   curta do que o avaliador está vendo, link para o repositório, comparação template × LLM lado a lado.
   Manter: tema claro/escuro, funcionar no celular, escapar todo texto vindo da API (sem `innerHTML`).
5. *(Opcional)* Fazer o Reclame Aqui passar pelo `decidir` antes de ir para humano (o dossiê ganharia
   ações sugeridas).

### Orquestração entre agentes

**Plano detalhado do trabalho em paralelo (Claude Code + Antigravity): [`docs/plano-paralelo.md`](docs/plano-paralelo.md).**
Lá estão a divisão de arquivos, as fases e o contrato do `public/diagnostico.json`.

- Uma branch por tarefa, cada uma vira PR; o Caio faz o merge (push na `main` publica na Vercel).
- Tarefas que não tocam os mesmos arquivos podem rodar em paralelo: frontend (`public/`) e backend
  (`servicos/`, `grafo/`, `tests/`). O README entra por último, descrevendo o que ficou pronto.
- Testes sem LLM (`SEM_LLM=1` ou o mock de `tests/test_api.py`): as cotas são compartilhadas.
- Decisão de negócio nova: parar e perguntar ao Caio.
