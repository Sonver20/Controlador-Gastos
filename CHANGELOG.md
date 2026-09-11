# Changelog

Todas as mudanças notáveis deste projeto são documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto segue [Semantic Versioning](https://semver.org/lang/pt-BR/)
(`MAJOR.MINOR.PATCH`) a partir da versão 2.0.0.

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
