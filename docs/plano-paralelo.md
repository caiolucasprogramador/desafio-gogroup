# Plano paralelo: Claude Code + Antigravity

Dois agentes trabalhando ao mesmo tempo, **sem tocar nos mesmos arquivos**. Eles se encontram num
**contrato**: o formato do `public/diagnostico.json` (seção 3). O Claude produz o JSON com números
reais; o Antigravity constrói as páginas que o leem. O Caio revisa e faz o merge.

Leitura obrigatória para os dois: `CLAUDE.md` (regras do projeto, decisões já tomadas).

---

## 1. Divisão

| | **Claude Code** | **Antigravity** |
|---|---|---|
| Papel | Dados, backend, testes, documentação | Interface (HTML/CSS/JS) |
| Branch | `feat/diagnostico-dados` | `feat/frontend` |
| Pode alterar | `scripts/`, `atendimento/`, `tests/`, `main.py`, `public/diagnostico.json`, `README.md`, `CLAUDE.md`, `docs/` | `public/index.html`, `public/diagnostico.html`, `public/assets/` (se criar) |
| **Não pode** | `public/*.html` | tudo fora de `public/` (exceto `public/diagnostico.json`, que é do Claude) |
| Acessa dados do case? | Sim (`case_*/`, `dados/`), só localmente | **Não.** Nunca abre `case_*/`, `dados/` nem o PDF |

**Por que o Antigravity não lê os dados:** ele envia o que lê para o modelo dele (Gemini). Os dados do
case são confidenciais e só podem ir a um LLM anonimizados, pelo nó `anonimizar`. Ele não precisa
deles: trabalha só com o contrato e com o JSON de exemplo.

---

## 2. Sequência

### Fase 0 · Claude (antes do Antigravity começar, ~15 min)
1. Criar `public/diagnostico.json` **com valores de exemplo** seguindo o contrato da seção 3
   (números inventados e redondos, marcados com `"exemplo": true`).
2. Servir `public/` localmente no FastAPI (`/diagnostico.html` e `/diagnostico.json`), igual à Vercel.
3. Commit na `main` → as duas branches nascem daqui.

### Fase 1 · em paralelo

**Claude: `feat/diagnostico-dados`**
1. `scripts/gerar_diagnostico.py`: lê `case_atendimento/` + `dados/` e grava `public/diagnostico.json`
   com os números **reais**, só agregados.
2. `tests/test_diagnostico.py`: valida o contrato (todas as chaves, tipos, percentuais somando ~100%)
   e a **privacidade**: o JSON não pode conter padrões de ID (`CV\d+`, `CL\d+`, pedidos `G[A-Z]\d+`),
   e-mail, telefone, CPF nem nenhum trecho de mensagem.
3. Conferir os números contra os já registrados no `CLAUDE.md` (custo R$ 108.299, RA 47%, 784/553…).
4. Rascunho do `README.md` com as respostas às 4 perguntas (mesmos números do JSON).

**Antigravity: `feat/frontend`**
1. `public/diagnostico.html`: página que faz `fetch("diagnostico.json")` e responde às 4 perguntas
   (seção 4). Se `exemplo === true`, mostrar uma faixa discreta "dados de exemplo".
2. Navegação entre as duas páginas ("Diagnóstico" | "Testar o agente") nas duas.
3. Melhorias em `public/index.html` (seção 5).

### Fase 2 · integração (Caio + Claude)
1. Caio revisa o PR do Antigravity (diff + abrir as páginas) e faz o merge.
2. Claude faz merge da `main` na própria branch, roda o script (JSON real), roda `pytest`, abre o site
   local e confere as duas páginas com os números reais.
3. Caio faz o merge final e o push → Vercel publica.
4. Caio decide sobre `scripts/rotulos_propostos.py` e torna o repositório público.

---

## 3. Contrato: `public/diagnostico.json`

Valores monetários em reais (número, sem formatação). Percentuais como fração de 0 a 1.
Listas já vêm **ordenadas** como devem aparecer. Nenhum ID, nome ou texto de cliente.

**Duas escalas (importante para a página):** os arquivos do case são uma amostra de 1 em cada 3 clientes.
- Todo campo `conversas` é contagem **da amostra** (4.000 conversas no total).
- Todo campo `custo`/`custo_estimado`/`total_custo` é o custo **trimestral da operação inteira**
  (custo da amostra × `totais.fator_expansao`).
- `totais.conversas_estimadas` = `conversas` × `fator_expansao` (≈ 12.000 no trimestre): use este
  número quando ele aparecer ao lado do custo, para não sugerir que 4.000 conversas custam R$ 108 mil.
- Percentuais não mudam com a expansão.

```json
{
  "exemplo": true,
  "gerado_em": "2026-11-09",
  "periodo": { "inicio": "2026-07-02", "fim": "2026-09-30", "dias": 90 },

  "totais": {
    "conversas": 4000,
    "fator_expansao": 3,
    "conversas_estimadas": 12000,
    "custo_estimado": 108000,
    "marcas": 9
  },

  "classificacao": {
    "amostra_gabarito": 96,
    "acerto_agente": 0.95,
    "acerto_tag_manual": 0.6,
    "recall_motivos": 0.98,
    "saude_detectada": "14/14",
    "modelo": "gemini-3.5-flash-lite",
    "observacao": "Gabarito rotulado por IA, sem validação humana."
  },

  "p1_por_que_procuram": {
    "categorias": [
      { "categoria": "entrega", "rotulo": "Entrega", "conversas": 1500, "pct_conversas": 0.375, "custo": 40000, "pct_custo": 0.37 }
    ],
    "motivos": [
      { "motivo": "atraso", "rotulo": "Atraso na entrega", "categoria": "entrega", "conversas": 700, "pct_conversas": 0.175, "custo": 20000, "pct_custo": 0.185, "gravidade": 50 }
    ],
    "canais": [
      { "canal": "reclame_aqui", "rotulo": "Reclame Aqui", "conversas": 400, "pct_conversas": 0.1, "custo_unitario": 42.0, "custo": 50000, "pct_custo": 0.47 }
    ]
  },

  "p2_contatos_evitaveis": {
    "total_custo": 50000,
    "itens": [
      { "id": "recontato", "rotulo": "Cliente voltando a perguntar", "conversas": 900, "custo": 28000,
        "como_evitar": "Responder o primeiro contato por completo e avisar proativamente." }
    ]
  },

  "p3_atacar_primeiro": {
    "criterio": "Custo trimestral × gravidade × facilidade de ação.",
    "itens": [
      { "rank": 1, "foco": "Reclame Aqui", "porque": "10% dos contatos e 47% do custo.", "conversas": 400, "custo": 50000 }
    ]
  },

  "p4_sozinho_ou_pessoa": {
    "fila_avaliada": 1337,
    "automatico": 784,
    "humano": 553,
    "resolucao_completa_pct": 0.42,
    "por_acao": [
      { "acao": "solicitar_informacoes", "rotulo": "Pedir informação ao cliente", "modo": "automatico", "conversas": 222 }
    ],
    "por_fila_humana": [
      { "fila": "atendimento", "rotulo": "Atendimento", "conversas": 170 }
    ],
    "politicas_faltantes": [
      { "motivo": "brinde_faltante", "rotulo": "Brinde faltante", "conversas": 92, "sugestao": "Política de reenvio do brinde." }
    ]
  }
}
```

Mudança no contrato = combinar antes (o Caio avisa o outro agente).

**Histórico do contrato**
- 2026-11-09: adicionados `totais.fator_expansao` e `totais.conversas_estimadas` (aprovado pelo Caio).
  Só acréscimo: nenhum campo existente mudou de nome ou de significado.

---

## 4. Página Diagnóstico (Antigravity)

Público: a **liderança** do atendimento e o avaliador do desafio. Deve ser lida em 1 minuto.

- **Topo:** uma frase-tese + 3 a 4 números grandes (conversas, custo estimado, % automatizável,
  acerto do agente contra a tag manual). Ao lado do custo, mostrar `conversas_estimadas` (≈ 12 mil
  no trimestre) e uma nota curta: "análise numa amostra de 4.000 conversas (1 em cada 3 clientes);
  custos estimados para a operação inteira".
- **Uma seção por pergunta do enunciado**, com o título sendo a própria pergunta:
  1. *Por que os clientes nos procuram, e qual o peso real de cada motivo?* Barras horizontais por
     motivo ou categoria comparando **% das conversas × % do custo** (o contraste é a mensagem). Canais em tabela.
  2. *Quais contatos poderiam não existir?* Itens com custo e "como evitar".
  3. *O que atacar primeiro, e com que critério?* Lista ranqueada com o critério explícito.
  4. *O que o sistema faz sozinho e o que precisa de pessoa?* Barra 59% × 41%, ações automáticas,
     filas humanas e "políticas que destravariam mais automação".
- **Rodapé:** limitações (de `classificacao.observacao`) e link para o repositório.
- Gráficos em HTML/CSS ou SVG inline (sem biblioteca é preferível). Se usar biblioteca, de CDN com versão fixa.
- Números formatados em pt-BR (`R$ 108.299`, `47%`).

## 5. Melhorias em `index.html` (Antigravity)

- Durante o carregamento, acender os nós do grafo em sequência (hoje o botão só diz "Atendendo…").
- Introdução de 10 segundos: o que é a tela e o que testar.
- Link para o repositório e para o Diagnóstico.
- Com "Reescrever com LLM" marcado: mostrar template e texto do LLM lado a lado. *Depende da API devolver
  o template também; se precisar, o Antigravity pede e o Claude adiciona o campo `resposta_template`.*
- **Não mudar** os nomes de campo que a página lê da API (`/api/atender`, `/api/exemplos`, `/api/opcoes`).

## 6. Regras comuns (critério de pronto)

- Tema claro e escuro; funcionar a 400 px de largura sem rolagem horizontal da página.
- Todo texto vindo da API ou do JSON inserido com `textContent`, nunca `innerHTML`.
- `python -m pytest -q` passando.
- Sem chamadas a LLM em testes (`SEM_LLM=1`); as cotas são compartilhadas.
- Nada de dados do case, IDs ou textos de conversa em arquivo versionado.
- Decisão de negócio nova (ex.: um número que muda a recomendação): parar e perguntar ao Caio.
- Commits locais na própria branch; merge e push só pelo Caio.
