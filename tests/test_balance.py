"""
tests/test_balance.py - Saldo da conta: definir, debitar, devolver e preservar campos.
"""

import unittest
from decimal import Decimal
from database import Database
from services.finance import FinanceService
from services.scheduler import SchedulerService


class TestDatabaseBalance(unittest.TestCase):
    """Testa operacoes de saldo e subtracao."""

    def setUp(self):
        self.db = Database(db_path=":memory:")
        self.finance = FinanceService(self.db)
        self.scheduler = SchedulerService(self.db)

    def test_get_balance_default_zero(self):
        res = self.finance.get_balance()
        self.assertTrue(res["success"])
        self.assertEqual(res["balance"], Decimal("0"))

    def test_set_balance(self):
        res = self.finance.set_balance(1000.0)
        self.assertTrue(res["success"])
        self.assertEqual(res["balance"], Decimal("1000.00"))
        fetched = self.finance.get_balance()
        self.assertEqual(fetched["balance"], Decimal("1000.00"))

    def test_set_balance_overwrites(self):
        self.finance.set_balance(500.0)
        self.finance.set_balance(200.0)
        res = self.finance.get_balance()
        self.assertEqual(res["balance"], Decimal("200.00"))

    def test_subtract_from_balance(self):
        self.finance.set_balance(1000.0)
        res = self.finance.subtract_from_balance(150.50)
        self.assertTrue(res["success"])
        self.assertEqual(res["balance"], Decimal("849.50"))
        fetched = self.finance.get_balance()
        self.assertEqual(fetched["balance"], Decimal("849.50"))

    def test_subtract_from_balance_negative_result(self):
        self.finance.set_balance(50.0)
        res = self.finance.subtract_from_balance(100.0)
        self.assertTrue(res["success"])
        self.assertEqual(res["balance"], Decimal("-50.00"))

    def test_subtract_from_balance_no_prior_balance(self):
        res = self.finance.subtract_from_balance(100.0)
        self.assertTrue(res["success"])
        self.assertEqual(res["balance"], Decimal("-100.00"))

    def test_set_balance_preserves_salary(self):
        self.scheduler.set_salary(5000.0)
        self.finance.set_balance(1000.0)
        salary = self.scheduler.get_salary()
        self.assertEqual(salary["salary"], Decimal("5000.00"))

    def test_subtract_from_balance_preserves_salary(self):
        """Bug corrigido no refactor: subtract_from_balance usava
        INSERT OR REPLACE so com a coluna 'amount', o que zerava salario
        e datas de credito a cada despesa registrada."""
        self.scheduler.set_salary(5000.0)
        self.scheduler.set_last_salary_month("2026-01")
        self.finance.subtract_from_balance(100.0)
        salary = self.scheduler.get_salary()
        self.assertEqual(salary["salary"], Decimal("5000.00"))
        self.assertEqual(salary["last_salary_month"], "2026-01")

    def test_subtract_from_balance_no_float_drift_over_many_calls(self):
        """Muitas subtracoes de 0.10 nao devem acumular erro de float."""
        self.finance.set_balance("100.00")
        for _ in range(10):
            self.finance.subtract_from_balance("0.10")
        balance = self.finance.get_balance()
        self.assertEqual(balance["balance"], Decimal("99.00"))
