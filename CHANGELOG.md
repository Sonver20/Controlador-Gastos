# Changelog

Todas as mudanças notáveis deste projeto são documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto segue [Semantic Versioning](https://semver.org/lang/pt-BR/)
(`MAJOR.MINOR.PATCH`) a partir da versão 2.0.0.

## [3.1.0] - 2026-09-22

### Adicionado
- **Internacionalização (PT/EN)**: engrenagem de Configurações no rodapé
  da barra lateral, com seletor de idioma. Novo `scripts/core/i18n.js`
  concentra o dicionário PT/EN e traduz tanto os elementos estáticos
  (`data-i18n`) quanto o conteúdo gerado dinamicamente por cada
  `scripts/features/*.js`; mensagens de sucesso/erro vindas do backend
  passaram a trazer um campo `key` (e `params`) opcional, usado pelo
  frontend para traduzir o toast (cai para o texto em português já
  existente quando a chave não é reconhecida, então nada quebra).
  `config.py` ganha `get_language`/`set_language`. `README.en.md`
  criado, com link cruzado a partir do `README.md`.
- **Cor principal personalizável**: no mesmo painel de Configurações,
  5 paletas prontas (roxo/violeta — padrão e cor histórica do app, azul,
  verde, vermelho, laranja) ou uma cor customizada via seletor de cor,
  com escala 50-900 gerada automaticamente (preservando matiz/saturação
  da cor escolhida). Novo `scripts/core/color.js`; `config.py` ganha
  `get_primary_color`/`set_primary_color`. A troca é instantânea porque
  o Tailwind (`assets/tailwind.js`) recompila ao vivo quando
  `tailwind.config` muda.

### Verificado
- Investigado o relato de que excluir uma despesa não devolveria o
  valor ao saldo: revisão de ponta a ponta (`modals.js` → `app.py` →
  `services/finance.py` → `database.py`) e a suíte de testes completa
  (170 testes, incluindo casos dedicados a esse cenário) não reproduziu
  o problema — o comportamento correto já está em vigor desde a correção
  da v2.2.0.

## [3.0.0] - 2026-09-21

### Adicionado
- **Despesas Mensais**: templates de gastos recorrentes (novas tabelas
  `monthly_groups`/`monthly_items` + `services/monthly.py` + view própria
  no frontend). Cada item tem sua própria categoria/subcategoria (diferente
  da Nova Despesa, que compartilha uma categoria). Todo mês, ao abrir o
  app, os grupos pendentes são lançados como despesas e o total é debitado
  do saldo automaticamente (`check_monthly_expenses`); também é possível
  aplicar manualmente com "Aplicar agora".

### Removido
- **Parser de Texto / Notificações**: a extração automática de descrição +
  valor a partir de texto colado não funcionava bem na prática e foi
  removida (view, navegação, métodos `parse_raw_text` e
  `save_parsed_expenses` da Api e do FinanceService, e testes).

### Modificado
- Frontend modularizado: o monólito `script.js` foi dividido em
  `scripts/core/` (`api.js` com retry/timeout, `state.js`, `utils.js`,
  `theme.js`, `toast.js`), `scripts/features/` (`dashboard.js`,
  `register.js`, `monthly.js`, `tree.js`, `balance.js`, `calendar.js`,
  `modals.js`) e `scripts/main.js` (navegação, atalhos, init), todos sob o
  namespace `window.CG`.
- Dependências baixadas para `assets/` (Tailwind CSS e fonte Phosphor
  Icons com CSS local): o app não precisa mais de internet para abrir.

## [2.2.0] - 2026-09-11

### Adicionado
- `decimal_utils.py` e o pacote `services/` (`payroll.py`, `finance.py`,
  `scheduler.py`), separando `database.py` em camadas: persistência pura
  (SQL direto) vs. regras de negócio (impostos, saldo, ciclo de salário).

### Corrigido
- Excluir uma despesa agora **devolve o valor dela ao saldo** — antes não
  mexia no saldo, o que era inconsistente com editar (que já ajusta o
  saldo pela diferença desde a v2.0.0).
- Diversos erros ortográficos em todo o app (textos da interface e
  mensagens de erro): acentos faltando como "Preço", "Árvore", "Não",
  "Salário", "Férias", "Descrição", entre outros.

### Modificado
- Paleta de cores trocada de verde (emerald) para roxo (violet) em toda
  a interface, incluindo o ícone gerado pelo `install.sh`.
- `database.py` reduzido de ~960 para ~590 linhas: métodos de cálculo
  (`calcular_ferias`, `resolve_amount`) e de regra de negócio (ajuste de
  saldo, ciclo de 30 dias) migraram para `services/`. `app.py` (`Api`)
  agora delega para os services; leituras puras continuam batendo direto
  em `database.py`.

## [2.1.0] - 2026-09-09

### Adicionado
- Campo de data editável no modal de edição de despesa (a data podia ser
  vista, mas não alterada).

### Corrigido
- Os botões "Voltar" e "Voltar às categorias" da Árvore de Gastos paravam
  de responder depois de entrar em uma categoria. Causa: `viewMonthCategories`
  chamava `switchView('view-tree')`, que por sua vez sempre disparava
  `showMonthsList()` como efeito colateral — isso resetava o mês/categoria
  selecionados logo depois de terem sido definidos, deixando as guardas
  `if (currentTreeMonth)` dos botões de voltar sempre falsas. Substituído
  por `ensureTreeViewActive()`, que só garante que a seção esteja visível,
  sem mexer no estado de navegação.

## [2.0.0] - 2026-09-08

Ponto de partida da adoção de Semantic Versioning, reunindo o trabalho já
feito no projeto até aqui.

### Adicionado
- Precisão monetária com `decimal.Decimal` de ponta a ponta (banco de
  dados, backend e ponte com o frontend), substituindo `float`.
- Subcategorias de despesas, com um nível a mais de navegação na Árvore
  de Gastos (Mês → Categoria → Subcategoria → Despesas), que só aparece
  quando a categoria realmente usa subcategorias.
- Lançamento de despesas por preço unitário × quantidade, com suporte a
  quantidades fracionárias (ex.: peso em kg).
- "Nova Despesa" unificada: uma categoria/subcategoria compartilhada e
  uma lista de produtos (nome, preço, quantidade com stepper +/-),
  substituindo o antigo "Cadastro em Massa" (texto colado).
- Calendário de salário com data de recebimento configurável, projetando
  os próximos recebimentos a cada 30 dias reais (em vez de assumir o
  mesmo dia do mês para todos os meses).
- Migração automática de bancos de dados criados por versões anteriores
  do app (colunas `REAL` → `DECIMAL`, novas colunas de subcategoria/
  quantidade/preço unitário).

### Corrigido
- `subtract_from_balance` zerava salário e data de crédito a cada despesa
  registrada, por fazer `INSERT OR REPLACE` sem preservar todos os campos
  da tabela `balance`.
- `save_parsed_expenses` descontava do saldo o total de **todos** os
  itens enviados pelo parser de texto, mesmo os rejeitados (negativos ou
  vazios), em vez de somar apenas os que foram de fato inseridos.
- Cadastro em massa interpretava valores com vírgula decimal (ex.:
  "5,50") no lugar errado, por usar `rsplit` em vez de `split` ao separar
  descrição e valor.
- Editar o preço (ou a quantidade) de uma despesa não ajustava o saldo,
  nem para mais nem para menos.
- Conexão SQLite sem rollback explícito em caso de exceção: no banco
  `:memory:` (conexão persistente, reaproveitada entre chamadas), uma
  escrita não commitada de uma operação que falhasse ficava "pendurada"
  na conexão e era commitada silenciosamente pela próxima chamada
  bem-sucedida que a reaproveitasse.

### Modificado
- `database.py` reorganizado para eliminar duplicação: o gerenciador de
  contexto `_connection()` substitui ~22 blocos repetidos de abrir/fechar
  conexão (e agora garante rollback em caso de erro); `_fetch_balance_row`/
  `_save_balance_row`, `_grouped_totals` e `_table_columns` centralizam
  padrões que antes estavam copiados em vários métodos.
