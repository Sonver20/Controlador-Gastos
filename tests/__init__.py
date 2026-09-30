"""
tests/ - Testes automatizados de toda a lógica do Controlador de Gastos.

Como executar (a partir da raiz do projeto):
    python3 tests/main.py             # todos os testes, saída detalhada
    python3 tests/main.py -q          # silencioso: só falhas e o resumo
    python3 tests/main.py config api  # só os módulos cujo nome contém "config" ou "api"
    python3 -m unittest tests.test_config -v   # um módulo específico

Cada arquivo `test_*.py` cobre um assunto; o `main.py` descobre todos
sozinho -- um arquivo ou classe de teste novo entra na execução sem
precisar ser registrado em nenhuma lista.

NOTA SOBRE OS VALORES MONETÁRIOS NOS TESTES
-------------------------------------------
`Database` (database.py), `FinanceService` e `SchedulerService`
(services/) trabalham e retornam `decimal.Decimal` diretamente, então os
testes que usam `self.db`/`self.finance`/`self.scheduler` comparam contra
`Decimal("X.XX")`.

`Api` (app.py) é a ponte com o JavaScript: ela converte todo `Decimal` em
string antes de retornar (pywebview serializa a resposta como JSON, que
não sabe lidar com Decimal). Por isso, os testes que usam `self.api`
(classes que herdam de `tests.helpers.ApiTestCase`) comparam os valores
monetários contra strings como "X.XX".
"""

import os
import sys

# Garante que os módulos do projeto (database, services, app...) sejam
# importáveis, qualquer que seja o jeito de executar os testes.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
