# Changelog

Todas as mudanças notáveis deste projeto são documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto segue [Semantic Versioning](https://semver.org/lang/pt-BR/)
(`MAJOR.MINOR.PATCH`) a partir da versão 2.0.0.

## [3.4.1] - 2026-09-29

### Modificado
- **Testes modularizados em `tests/`**: o `tests.py` único (quase 1.900
  linhas) foi dividido em 18 módulos por assunto (`test_expenses_crud`,
  `test_migrations`, `test_variable_price`, `test_measure_units`,
  `test_config`, `test_api_bridge` etc.), mais `tests/helpers.py` (utilitários
  compartilhados) e `tests/main.py`, que executa tudo:
  `python3 tests/main.py` (`-q` para silencioso; nomes de módulo filtram, ex.:
  `python3 tests/main.py config api`). O `main.py` **descobre os arquivos
  sozinho** — antes, um teste novo só rodava se a classe fosse registrada à mão
  numa lista no rodapé do arquivo, e esquecer disso fazia o teste simplesmente
  não executar. O código de saída é 0 quando tudo passa e 1 quando há falha.
  Nenhum teste foi perdido ou renomeado na divisão (mesmos nomes de classe e de
  método). **Se você atualizar por cima da pasta antiga, apague o `tests.py`
  da raiz** — a cópia por cima não remove arquivos.
- **Testes da `Api` não tocam mais nos arquivos reais**: `Api()` abre o
  `gastos.db` e o `app_config.json` da pasta do projeto, então rodar os testes
  abria (e migrava) o banco de quem os executava, e ainda deixava pastas
  temporárias para trás. Agora as classes que herdam de `ApiTestCase` rodam
  com a pasta base redirecionada para um diretório temporário, apagado no fim
  de cada teste.

### Removido
- 3 testes redundantes entre as classes de peso variável e de unidades (o
  que tinham de único foi mesclado nos testes que ficaram: 195 → 192 testes,
  sem perda de cobertura — quebrar o código de propósito continua sendo
  acusado pelos mesmos casos).

## [3.4.0] - 2026-09-29

### Adicionado
- **Unidade no peso/volume: kg, g, ml e L.** O campo de peso da Nova
  Despesa, do Editar Despesa e do Adicionar item virou "Peso ou volume",
  com uma unidade clicável ao lado (kg, g, ml, L), então dá para anotar
  740 g de laranja ou 1,5 L de suco. A unidade só acompanha o número
  digitado: não há conversão (740 g continua sendo 740 g) e nada disso
  entra em nenhuma conta. Sem número, a unidade é descartada. Na Árvore de
  Gastos o item mostra como foi digitado ("740 g", "1,5 L", "500 ml").

### Modificado
- **Nova Despesa: volta ao layout compacto de antes.** A linha de cada
  produto é de novo uma só (nome, preço, quantidade, subtotal, remover), e
  o peso ganhou apenas uma linha fina logo abaixo, com o interruptor
  "Peso variável", o número e a unidade. O comportamento do interruptor
  não mudou (desligado: preço × quantidade; ligado: o valor é o total e
  não multiplica).
- **Banco de dados**: a coluna `weight_kg` (v3.3.1) foi renomeada para
  `measure_value` e ganhou `measure_unit`. A migração é automática ao
  abrir o app: os pesos já cadastrados são mantidos e marcados como "kg".
  A API passou a usar `measure_value`/`measure_unit` no lugar de
  `weight_kg`.

## [3.3.1] - 2026-09-28

### Modificado
- **"Peso variável" redesenhado**: na 3.3.0 o interruptor trocava a
  quantidade por um campo de peso (e escondia o +/-), o que impedia
  registrar ao mesmo tempo *quantos itens* e *quanto pesam* (ex.: 3
  pacotes de arroz de 5 kg; ou 4 laranjas que somaram 740 g). Agora as
  duas coisas são independentes:
  - a **quantidade** (com o +/- de sempre) nunca some nem muda de
    significado, em nenhum modo;
  - o **peso (kg)** é um campo próprio, opcional e sempre visível, logo
    abaixo do nome do produto, com o interruptor "Peso variável" à frente
    dele. É só uma anotação: nunca entra em nenhuma conta;
  - o **interruptor** faz uma única coisa: desligado, a despesa funciona
    normalmente (preço unitário × quantidade); ligado, o valor digitado é
    o total pago e deixa de ser multiplicado pela quantidade. O único
    ajuste visual é o rótulo do preço ("Preço" ⇄ "Valor total pago").
  Vale para Nova Despesa, Editar Despesa e Adicionar item. Backend: nova
  coluna `weight_kg` em `expenses` (migração automática, nula para
  despesas antigas). Na Árvore de Gastos, cada detalhe aparece separado:
  "2 × R$ 4,50", "4 un. · valor total (peso variável)", "0,74 kg".

### Corrigido
- **Não dava para alterar o peso de uma despesa já cadastrada** (o
  interruptor no modal de edição só reaproveitava o campo de quantidade).
  Agora o modal de edição tem o campo de peso próprio, carregado com o
  valor salvo e editável (ou apagável).

## [3.3.0] - 2026-09-28

### Adicionado
- **Peso variável (itens comprados por kg)**: novo interruptor "Peso
  variável" por produto na Nova Despesa, no modal de Editar Despesa e no
  novo "Adicionar item" da Árvore de Gastos. Ligado, o valor digitado
  passa a ser o **total pago** (rótulo vira "Valor total pago") e a
  quantidade vira só o **peso em kg**, informativo — *não multiplica*.
  Resolve o caso de 4 laranjas que pesaram 0,740 kg e custaram R$ 2,95
  no total: antes, qualquer quantidade multiplicaria o valor (4 × 2,95 =
  11,80, errado). Os botões +/- somem nesse modo (não faz sentido somar
  1 kg por clique) e o subtotal já reflete o total exato na hora. Na
  Árvore de Gastos, o item mostra "0,74 kg · valor total (peso
  variável)". Backend: nova coluna `is_variable_price` em `expenses`
  (migração automática, padrão 0 — nada muda para despesas antigas);
  `resolve_amount` ganhou o parâmetro `is_variable_price`, e o "preço por
  kg" derivado (total ÷ peso) é gravado só para referência, nunca usado
  para recalcular o valor. Itens normais e de peso variável podem ser
  misturados na mesma Nova Despesa. (Despesas Mensais não ganharam esse
  modo nesta versão.)
- **Renomear categorias e subcategorias**: ícone de lápis nos cards de
  categoria e de subcategoria e ao lado do título da lista de despesas.
  O renome é **global** — vale para todos os meses e também para os
  templates de Despesa Mensal, já que categoria é só uma etiqueta de
  texto reaproveitada. Subcategorias são renomeadas dentro da própria
  categoria (uma "Carnes" em Açougue não afeta uma "Carnes" em
  Restaurante). Renomear o balde "Sem subcategoria" dá um nome aos itens
  sem subcategoria; deixar o novo nome vazio remove a subcategoria.
- **Adicionar item direto na categoria/subcategoria**: botão "Adicionar
  item" na lista de despesas da Árvore de Gastos, já com categoria e
  subcategoria preenchidas — não precisa voltar à Nova Despesa e
  redigitar tudo. O item entra com a data/hora de agora, como na Nova
  Despesa (para outra data, use o lápis de editar depois).
- **Yuan chinês (CNY)** na lista de moedas de exibição.

### Corrigido
- **Compras da mesma subcategoria em dias diferentes pareciam uma só**:
  as despesas ficavam numa lista contínua, só com a data em cada linha.
  Agora a lista é agrupada por dia, com um cabeçalho ("domingo,
  20/09/2026") e o total daquele dia; a coluna da tabela passou de
  "Data" para "Hora", já que a data está no cabeçalho do grupo.

## [3.2.0] - 2026-09-27

### Adicionado
- **Moeda de exibição configurável**: no painel de Configurações (Geral),
  novo seletor de moeda (Real, Dólar Americano, Euro, Libra Esterlina)
  para quem usa o app em outro idioma e não lida em Reais no dia a dia.
  É só formatação — o número digitado não muda, apenas o símbolo/código
  exibido (`Intl.NumberFormat` já sabe renderizar o símbolo certo por
  locale a partir do código ISO 4217 configurado). Nesta primeira versão
  a lista fica limitada a moedas comuns de 2 casas decimais (moedas que
  funcionam diferente, como o Iene, ficam de fora por enquanto). Novo
  `scripts/core/currency.js`; `config.py` ganha `currency` (padrão
  `"BRL"`) e `app.py` ganha `get_currency`/`set_currency`. O cálculo de
  férias (INSS/IRRF) continua sendo feito com tributos brasileiros
  independente da moeda de exibição escolhida — trocar o símbolo não
  muda a legislação usada no cálculo.

### Modificado
- **Configurações reorganizadas em uma janela própria**: a engrenagem
  saiu do rodapé da barra lateral (onde abria um mini popover) e foi
  para o cabeçalho, no lugar onde ficava o botão de alternar tema
  claro/escuro. Clicar nela agora abre uma janela no mesmo formato dos
  outros modais do app (Editar Despesa, Saldo & Salário, Calcular
  Férias), com um menu de categorias à esquerda — só "Geral" por
  enquanto, já pensado para crescer — reunindo tema, idioma, cor
  principal e a nova moeda de exibição. Como o tema deixou de ter um
  botão de alternância dedicado no cabeçalho, ele agora é escolhido por
  dois botões explícitos ("Claro"/"Escuro") dentro dessa janela, no
  mesmo padrão dos botões de idioma e cor (`scripts/core/theme.js`
  reescrito nesse sentido; `CG.theme.toggle()` continua disponível por
  compatibilidade).
- **`config.py` refatorado para eliminar repetição**: os pares
  `get_x()`/`set_x()` (um por preferência, todos idênticos exceto pelo
  nome da chave) deram lugar a um único descriptor `ConfigProperty`,
  reutilizado por `theme`, `language`, `primary_color`, `currency` e
  `vacation_month` — cada preferência agora é só uma `property` (ex.:
  `cfg.theme`, `cfg.theme = "dark"`). O "success"/mensagem que o
  frontend recebe deixou de morar em `Config` (que agora é só
  armazenamento cru) e passou para a ponte com o JS em `app.py`, que já
  usava esses métodos.
- **i18n reorganizado em `scripts/core/locales/`**: o dicionário
  PT/EN, que vivia inteiro dentro de `i18n.js` (incluindo nomes de
  meses e dias da semana), foi separado em `locales/pt_BR.js` e
  `locales/en.js` — um arquivo por idioma, cada um só uma declaração de
  dados (`CG.locales.pt`/`CG.locales.en`). `i18n.js` ficou menor e passou
  a só carregar/gerenciar esses locales (idioma ativo, `t()`, `apply()`,
  `monthName()`, `weekdayShort()`), sem guardar nenhuma tradução
  diretamente.

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
  criado, com link cruzado a partir do `README.md`. Valores em dinheiro
  continuam em Reais (R$) nos dois idiomas — o que muda em inglês é só
  a convenção de separador decimal/milhar (1.234,56 → 1,234.56) e a
  ordem/formato de datas e horas (23/09/26 14:05 → 09/23/26 02:05 PM),
  via `Intl.NumberFormat`/`Intl.DateTimeFormat`.
- **Calendário próprio para seleção de data**: os campos de data (modal
  de Editar Despesa e modal de Saldo & Salário) deixaram de usar
  `<input type="date">` nativo, que o WebKitGTK sempre exibe no formato
  do idioma do sistema operacional (não do idioma escolhido no app).
  Novo `scripts/core/datepicker.js` substitui por um calendário próprio
  (popover), totalmente traduzido, que respeita o idioma selecionado.
  Pelo mesmo motivo (inputs nativos seguem o locale do SO, não o do
  app), todos os campos de quantidade e preço unitário/salário/saldo do
  app — Editar Despesa, Nova Despesa, Despesas Mensais, Saldo &
  Salário e Calcular Férias — passaram de `<input type="number">` para
  texto (`inputmode="decimal"`) formatado via
  `CG.utils.formatQuantity`/`formatPrice`, aceitando tanto vírgula
  quanto ponto na hora de digitar (`CG.utils.parseLocaleNumber`).
- **Cor principal personalizável**: no mesmo painel de Configurações,
  5 paletas prontas (roxo/violeta — padrão e cor histórica do app, azul,
  verde, vermelho, laranja) ou uma cor customizada via seletor de cor,
  com escala 50-900 gerada automaticamente (preservando matiz/saturação
  da cor escolhida). Novo `scripts/core/color.js`; `config.py` ganha
  `get_primary_color`/`set_primary_color`. A troca é instantânea porque
  o Tailwind (`assets/tailwind.js`) recompila ao vivo quando
  `tailwind.config` muda.

### Corrigido
- **Dashboard/despesas não carregavam**: a sequência de inicialização
  em `main.js` chamava `await CG.settings.init()` (idioma + cor) antes
  de `CG.dashboard.load()` sem isolar erros — se qualquer coisa nesse
  passo falhasse, a exceção cancelava toda a fila de inicialização
  seguinte, deixando a tela sem despesas mesmo com o banco intacto.
  Cada etapa (configurações, seletor de data) agora tem seu próprio
  `try/catch`, então uma falha ali não impede mais o carregamento de
  saldo/despesas. Também blindados: `CG.settings` contra
  `#btn-settings`/`#settings-popover` ausentes do DOM, e `CG.color`
  contra o Tailwind ainda não estar pronto.

### Removido
- **Resíduos do "Parser de Texto"**: essa funcionalidade (extrair
  despesas a partir de texto colado) já constava como removida da
  interface desde a v3.0.0, mas o código ainda tinha sobras. Removidos
  por completo: `parse_raw_text` e `save_parsed_expenses` de `app.py` e
  `services/finance.py` (incluindo o `import re`, que só servia a
  eles), e os testes correspondentes em `tests.py` — a classe
  `TestDatabaseRawParser` inteira e os casos de borda/Api relacionados
  espalhados em outras classes (17 testes no total).

### Verificado
- Investigado o relato de que excluir uma despesa não devolveria o
  valor ao saldo: revisão de ponta a ponta (`modals.js` → `app.py` →
  `services/finance.py` → `database.py`) e a suíte de testes completa
  (153 testes, incluindo casos dedicados a esse cenário) não reproduziu
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
