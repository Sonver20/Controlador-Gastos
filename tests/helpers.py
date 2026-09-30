"""
tests/helpers.py - Utilitários compartilhados pelos módulos de teste.
"""

import sys
import tempfile
import types
import unittest
from datetime import datetime
from unittest import mock

# Mock do módulo webview: o pywebview não precisa estar instalado para
# testar (app.py só o importa no topo). Precisa vir ANTES de `import app`.
if "webview" not in sys.modules:
    sys.modules["webview"] = types.ModuleType("webview")

import app as app_module  # noqa: E402  (depende do mock acima)
from database import Database  # noqa: E402
from services.finance import FinanceService  # noqa: E402
from services.monthly import MonthlyService  # noqa: E402
from services.scheduler import SchedulerService  # noqa: E402

Api = app_module.Api


def current_month() -> str:
    """Mês atual no formato "YYYY-MM" (o mesmo usado nas consultas por mês)."""
    return datetime.now().strftime("%Y-%m")


class ApiTestCase(unittest.TestCase):
    """
    Base dos testes da classe Api (a ponte com o JavaScript).

    `Api()` abre o `gastos.db` e o `app_config.json` da pasta do projeto.
    Para os testes NUNCA encostarem nos arquivos reais de quem os executa,
    a pasta base do app.py é redirecionada para um diretório temporário
    (apagado ao final de cada teste). Em seguida o banco de arquivo é
    trocado por um em memória, e os services -- que guardam uma referência
    ao banco antigo -- são recriados apontando para o novo.
    """

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        patcher = mock.patch.object(app_module, "BASE_DIR", tmp.name)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.api = Api()
        self.api.db = Database(db_path=":memory:")
        self.api.finance = FinanceService(self.api.db)
        self.api.scheduler = SchedulerService(self.api.db)
        self.api.monthly = MonthlyService(self.api.db, self.api.finance)
