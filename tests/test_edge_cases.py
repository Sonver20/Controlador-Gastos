"""
tests/test_edge_cases.py - Casos de borda do banco de dados.
"""

import unittest
import os
import tempfile
from decimal import Decimal
from database import Database
from services.finance import FinanceService


class TestDatabaseEdgeCases(unittest.TestCase):
    """Testa casos de borda e robustez."""

    def setUp(self):
        self.db = Database(db_path=":memory:")
        self.finance = FinanceService(self.db)

    def test_very_long_description(self):
        long_desc = "A" * 1000
        res = self.finance.add_expense("Teste", long_desc, 1.0)
        self.assertTrue(res["success"])
        fetched = self.db.get_expense(res["id"])
        self.assertEqual(fetched["data"]["description"], long_desc)

    def test_special_characters_in_category(self):
        res = self.finance.add_expense("Cafe & Lanche", "Pao de queijo", 5.0)
        self.assertTrue(res["success"])
        fetched = self.db.get_expense(res["id"])
        self.assertEqual(fetched["data"]["category"], "Cafe & Lanche")

    def test_unicode_characters(self):
        res = self.finance.add_expense("Alimentação", "Pão de queijo ☕", 5.0)
        self.assertTrue(res["success"])
        fetched = self.db.get_expense(res["id"])
        self.assertEqual(fetched["data"]["description"], "Pão de queijo ☕")

    def test_decimal_precision_is_exact(self):
        """Antes do refactor isso exigia assertAlmostEqual por causa do
        float; agora o valor e exato, entao usamos assertEqual direto."""
        res = self.finance.add_expense("Teste", "Precisao", 10.99)
        self.assertTrue(res["success"])
        fetched = self.db.get_expense(res["id"])
        self.assertEqual(fetched["data"]["amount"], Decimal("10.99"))

    def test_database_file_created(self):
        """Testa criacao com arquivo real (nao :memory:)."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            db = Database(db_path=path)
            fin = FinanceService(db)
            res = fin.add_expense("Teste", "Arquivo", 1.0)
            self.assertTrue(res["success"])
            self.assertTrue(os.path.exists(path))
        finally:
            os.unlink(path)

    def test_amount_persists_exactly_across_reconnect(self):
        """Reabre o mesmo arquivo (nova conexao) e confirma que o valor
        volta bit-a-bit igual, sem passar por REAL/float em nenhum momento."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            db1 = Database(db_path=path)
            add = FinanceService(db1).add_expense("Teste", "Precisao", "1999.99")
            db2 = Database(db_path=path)
            fetched = db2.get_expense(add["id"])
            self.assertEqual(fetched["data"]["amount"], Decimal("1999.99"))
        finally:
            os.unlink(path)


class TestDatabaseAdditionalEdgeCases(unittest.TestCase):
    """Testa casos de borda adicionais."""

    def setUp(self):
        self.db = Database(db_path=":memory:")
        self.finance = FinanceService(self.db)

    def test_add_expense_empty_category(self):
        res = self.finance.add_expense("", "Desc", 10.0)
        self.assertTrue(res["success"])
        fetched = self.db.get_expense(res["id"])
        self.assertEqual(fetched["data"]["category"], "")

    def test_add_expense_empty_description(self):
        res = self.finance.add_expense("Cat", "", 10.0)
        self.assertTrue(res["success"])
        fetched = self.db.get_expense(res["id"])
        self.assertEqual(fetched["data"]["description"], "")

    def test_update_expense_to_zero(self):
        add = self.finance.add_expense("Cat", "Desc", 10.0)
        self.finance.update_expense(add["id"], "Cat", "Desc", 0.0)
        fetched = self.db.get_expense(add["id"])
        self.assertEqual(fetched["data"]["amount"], Decimal("0.00"))

    def test_get_months_summary_empty_db(self):
        res = self.db.get_months_summary()
        self.assertTrue(res["success"])
        self.assertEqual(res["data"], [])

    def test_get_categories_by_month_no_data(self):
        res = self.db.get_categories_by_month("2000-01")
        self.assertTrue(res["success"])
        self.assertEqual(res["data"], [])

    def test_get_all_categories_empty_db(self):
        res = self.db.get_all_categories()
        self.assertTrue(res["success"])
        self.assertEqual(res["data"], [])

    def test_balance_and_expense_integration(self):
        # FinanceService.add_expense sempre desconta do saldo (a regra de
        # negocio mora no service agora, nao so na camada da Api).
        self.finance.set_balance(1000.0)
        self.finance.subtract_from_balance(200.0)
        self.finance.add_expense("Teste", "Teste", 100.0)
        balance = self.finance.get_balance()
        self.assertEqual(balance["balance"], Decimal("700.00"))

    def test_amount_with_many_decimals_is_rounded_half_up(self):
        """Antes precisava de assertAlmostEqual por causa do float; agora
        o valor e quantizado (ROUND_HALF_UP) de forma exata e previsivel."""
        res = self.finance.add_expense("Teste", "Precisao", 10.999)
        self.assertTrue(res["success"])
        fetched = self.db.get_expense(res["id"])
        self.assertEqual(fetched["data"]["amount"], Decimal("11.00"))

    def test_category_case_sensitivity(self):
        self.finance.add_expense("Alimentacao", "A", 10.0)
        self.finance.add_expense("alimentacao", "B", 20.0)
        cats = self.db.get_all_categories()
        self.assertEqual(len(cats["data"]), 2)

    def test_memory_db_isolation(self):
        db1 = Database(db_path=":memory:")
        db2 = Database(db_path=":memory:")
        FinanceService(db1).add_expense("A", "B", 10.0)
        self.assertEqual(len(db2.get_months_summary()["data"]), 0)
