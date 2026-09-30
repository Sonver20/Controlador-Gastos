"""
tests/test_aggregation.py - Agregações mensais e drill-down (mês → categoria → subcategoria).
"""

import unittest
from datetime import datetime
from decimal import Decimal
from database import Database
from services.finance import FinanceService


class TestDatabaseAggregation(unittest.TestCase):
    """Testa agregacoes mensais e drill-down."""

    def setUp(self):
        self.db = Database(db_path=":memory:")
        self.finance = FinanceService(self.db)
        # Inserir dados de dois meses distintos
        self.finance.add_expense("Alimentacao", "Mercado", 300.0)
        self.finance.add_expense("Alimentacao", "Padaria", 50.0)
        self.finance.add_expense("Transporte", "Uber", 100.0)
        self.finance.add_expense("Transporte", "Onibus", 50.0)
        # Datas futuras nao controlamos diretamente, mas como usamos
        # datetime('now') no DEFAULT, todos ficam no mes atual.

    def test_get_months_summary_returns_current_month(self):
        res = self.db.get_months_summary()
        self.assertTrue(res["success"])
        self.assertEqual(len(res["data"]), 1)
        self.assertEqual(res["data"][0]["count"], 4)
        self.assertEqual(res["data"][0]["total"], Decimal("500.00"))
        self.assertIsInstance(res["data"][0]["total"], Decimal)

    def test_get_categories_by_month(self):
        from datetime import datetime
        month = datetime.now().strftime("%Y-%m")
        res = self.db.get_categories_by_month(month)
        self.assertTrue(res["success"])
        self.assertEqual(len(res["data"]), 2)
        # Ordenado por total DESC: Alimentacao (350) > Transporte (150)
        self.assertEqual(res["data"][0]["category"], "Alimentacao")
        self.assertEqual(res["data"][0]["total"], Decimal("350.00"))
        self.assertEqual(res["data"][1]["category"], "Transporte")
        self.assertEqual(res["data"][1]["total"], Decimal("150.00"))

    def test_get_expenses_by_month_and_category(self):
        from datetime import datetime
        month = datetime.now().strftime("%Y-%m")
        res = self.db.get_expenses_by_month_and_category(month, "Alimentacao")
        self.assertTrue(res["success"])
        self.assertEqual(len(res["data"]), 2)
        descs = [r["description"] for r in res["data"]]
        self.assertIn("Mercado", descs)
        self.assertIn("Padaria", descs)

    def test_get_all_categories(self):
        res = self.db.get_all_categories()
        self.assertTrue(res["success"])
        self.assertEqual(res["data"], ["Alimentacao", "Transporte"])

    def test_get_categories_by_month_invalid(self):
        res = self.db.get_categories_by_month("2099-01")
        self.assertTrue(res["success"])
        self.assertEqual(len(res["data"]), 0)

    def test_months_summary_sum_has_no_float_drift(self):
        """Soma classica que gera erro em float (0.1 + 0.2 != 0.3) deve
        ser exata quando feita com Decimal."""
        db = Database(db_path=":memory:")
        fin = FinanceService(db)
        fin.add_expense("A", "x", "0.10")
        fin.add_expense("A", "y", "0.20")
        res = db.get_months_summary()
        self.assertEqual(res["data"][0]["total"], Decimal("0.30"))
