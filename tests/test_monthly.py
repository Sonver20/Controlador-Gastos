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
            {"description": "Aluguel", "unit_price": "500.00", "quantity": "1"},
            {"description": "Conta de luz", "unit_price": "120.50", "quantity": "1"},
        ]

    def _create_group(self, name, items=None, category="Moradia", subcategory=None):
        return self.monthly.create_group(
            name, category, subcategory, self._items() if items is None else items
        )

    def test_create_and_list_group(self):
        res = self._create_group("Contas da casa")
        self.assertTrue(res["success"])
        groups = self.monthly.list_groups()
        self.assertEqual(len(groups["data"]), 1)
        self.assertEqual(groups["data"][0]["total"], Decimal("620.50"))
        self.assertEqual(groups["data"][0]["category"], "Moradia")

    def test_update_group_changes_shared_classification(self):
        group_id = self._create_group("Contas")["id"]
        self.db.set_monthly_group_applied(group_id, "2026-09")

        result = self.monthly.update_group(
            group_id, "Casa", "Moradia", "Serviços",
            [{"description": "Internet", "unit_price": "80.00", "quantity": "1"}],
        )

        self.assertTrue(result["success"])
        group = self.monthly.list_groups()["data"][0]
        self.assertEqual((group["name"], group["category"], group["subcategory"]),
                         ("Casa", "Moradia", "Serviços"))
        self.assertEqual(group["last_applied_month"], "2026-09")
        self.assertEqual(group["items"][0]["description"], "Internet")

    def test_apply_group_inserts_expenses_and_debits_balance(self):
        group_id = self._create_group("Contas")["id"]
        result = self.monthly.apply_group(group_id)
        self.assertTrue(result["success"])
        self.assertEqual(result["total"], Decimal("620.50"))
        self.assertEqual(self.finance.get_balance()["balance"], Decimal("379.50"))
        summary = self.db.get_months_summary()
        self.assertEqual(summary["data"][0]["total"], Decimal("620.50"))

    def test_check_and_apply_no_duplicate_same_month(self):
        self._create_group("Contas")
        first_result = self.monthly.check_and_apply()
        self.assertEqual(first_result["applied_count"], 1)
        second_result = self.monthly.check_and_apply()
        self.assertEqual(second_result["applied_count"], 0)
        self.assertEqual(self.finance.get_balance()["balance"], Decimal("379.50"))

    def test_check_and_apply_next_month(self):
        previous_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        group_id = self._create_group("Contas")["id"]
        self.db.set_monthly_group_applied(group_id, previous_month)
        result = self.monthly.check_and_apply()
        self.assertEqual(result["applied_count"], 1)

    def test_delete_group_keeps_launched_expenses(self):
        group_id = self._create_group("Contas")["id"]
        self.monthly.apply_group(group_id)
        result = self.monthly.delete_group(group_id)
        self.assertTrue(result["success"])
        self.assertEqual(len(self.monthly.list_groups()["data"]), 0)
        self.assertEqual(len(self.db.get_months_summary()["data"]), 1)

    def test_create_group_requires_shared_category(self):
        result = self.monthly.create_group("Ruim", "", None, self._items())
        self.assertFalse(result["success"])

    def test_variable_price_item_applies_total_with_measure(self):
        items = [{
            "description": "Laranjas", "unit_price": "2.95", "quantity": "4",
            "is_variable_price": True, "measure_value": "740", "measure_unit": "g",
        }]
        group_id = self._create_group("Feira", items, "Mercado", "Frutas")["id"]

        result = self.monthly.apply_group(group_id)

        self.assertEqual(result["total"], Decimal("2.95"))
        expense = self.db.get_expenses_by_month_and_category(
            datetime.now().strftime("%Y-%m"), "Mercado", "Frutas"
        )["data"][0]
        self.assertEqual(expense["amount"], Decimal("2.95"))
        self.assertEqual(expense["quantity"], Decimal("4"))
        self.assertEqual(expense["is_variable_price"], 1)
        self.assertEqual(expense["measure_value"], Decimal("740"))
        self.assertEqual(expense["measure_unit"], "g")
