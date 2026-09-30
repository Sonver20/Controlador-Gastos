"""
tests/test_monthly.py - Despesas Mensais: templates recorrentes, aplicação e não-duplicação no mês.
"""

import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from database import Database
from services.finance import FinanceService
from services.monthly import MonthlyService


class TestMonthlyExpenses(unittest.TestCase):
    def setUp(self):
        self.db = Database(db_path=":memory:")
        self.finance = FinanceService(self.db)
        self.monthly = MonthlyService(self.db, self.finance)
        self.finance.set_balance("1000.00")

    def _items(self):
        return [
            {"category": "Moradia", "description": "Aluguel", "unit_price": "500.00", "quantity": "1"},
            {"category": "Energia", "description": "Conta de luz", "unit_price": "120.50", "quantity": "1"},
        ]

    def test_create_and_list_group(self):
        res = self.monthly.create_group("Contas da casa", self._items())
        self.assertTrue(res["success"])
        groups = self.monthly.list_groups()
        self.assertEqual(len(groups["data"]), 1)
        self.assertEqual(groups["data"][0]["total"], Decimal("620.50"))
        self.assertEqual(groups["data"][0]["items"][0]["category"], "Moradia")

    def test_apply_group_inserts_expenses_and_debits_balance(self):
        gid = self.monthly.create_group("Contas", self._items())["id"]
        res = self.monthly.apply_group(gid)
        self.assertTrue(res["success"])
        self.assertEqual(res["total"], Decimal("620.50"))
        self.assertEqual(self.finance.get_balance()["balance"], Decimal("379.50"))
        summary = self.db.get_months_summary()
        self.assertEqual(summary["data"][0]["total"], Decimal("620.50"))

    def test_check_and_apply_no_duplicate_same_month(self):
        gid = self.monthly.create_group("Contas", self._items())["id"]
        r1 = self.monthly.check_and_apply()
        self.assertEqual(r1["applied_count"], 1)
        r2 = self.monthly.check_and_apply()
        self.assertEqual(r2["applied_count"], 0)  # já aplicado no mês
        self.assertEqual(self.finance.get_balance()["balance"], Decimal("379.50"))

    def test_check_and_apply_next_month(self):
        from datetime import datetime
        prev = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        gid = self.monthly.create_group("Contas", self._items())["id"]
        self.db.set_monthly_group_applied(gid, prev)  # simula mês anterior
        res = self.monthly.check_and_apply()
        self.assertEqual(res["applied_count"], 1)

    def test_delete_group_keeps_launched_expenses(self):
        gid = self.monthly.create_group("Contas", self._items())["id"]
        self.monthly.apply_group(gid)
        res = self.monthly.delete_group(gid)
        self.assertTrue(res["success"])
        self.assertEqual(len(self.monthly.list_groups()["data"]), 0)
        self.assertEqual(len(self.db.get_months_summary()["data"]), 1)  # histórico intacto

    def test_create_group_rejects_items_without_category(self):
        res = self.monthly.create_group("Ruim", [{"description": "X", "unit_price": "10", "quantity": "1"}])
        self.assertFalse(res["success"])
