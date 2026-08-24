#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests.py - Testes automatizados para toda a logica do Controlador de Gastos.

Execute com:
    python3 tests.py -v
    python3 tests.py          # modo silencioso, so mostra falhas
"""

import unittest
import os
import sys
import tempfile

# Garante que os modulos do projeto sejam importaveis
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Database


# =============================================================================
# TESTES DO DATABASE (logica de negocio SQLite)
# =============================================================================
class TestDatabaseCRUD(unittest.TestCase):
    """Testa operacoes CRUD basicas."""

    def setUp(self):
        """Cria um banco em memoria para cada teste."""
        self.db = Database(db_path=":memory:")

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------
    def test_add_expense_success(self):
        res = self.db.add_expense("Alimentacao", "Mercado Extra", 150.50)
        self.assertTrue(res["success"])
        self.assertIsNotNone(res["id"])
        self.assertIn("sucesso", res["message"].lower())

    def test_add_expense_zero_amount(self):
        """Zero deve ser aceito (nao e negativo), mas e um edge case."""
        res = self.db.add_expense("Teste", "Gratis", 0.0)
        self.assertTrue(res["success"])

    def test_add_expense_negative_amount(self):
        """SQLite aceita REAL negativo; nossa logica nao bloqueia."""
        res = self.db.add_expense("Teste", "Devolucao", -50.0)
        self.assertTrue(res["success"])

    def test_add_expense_strips_whitespace(self):
        res = self.db.add_expense("  Alimentacao  ", "  Pao  ", 5.0)
        self.assertTrue(res["success"])
        fetched = self.db.get_expense(res["id"])
        self.assertEqual(fetched["data"]["category"], "Alimentacao")
        self.assertEqual(fetched["data"]["description"], "Pao")

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------
    def test_get_expense_found(self):
        add = self.db.add_expense("Transporte", "Uber", 23.90)
        res = self.db.get_expense(add["id"])
        self.assertTrue(res["success"])
        self.assertEqual(res["data"]["description"], "Uber")
        self.assertEqual(res["data"]["amount"], 23.90)

    def test_get_expense_not_found(self):
        res = self.db.get_expense(9999)
        self.assertFalse(res["success"])
        self.assertIsNone(res["data"])
        self.assertIn("nao encontrada", res["message"].lower())

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------
    def test_update_expense_success(self):
        add = self.db.add_expense("Lazer", "Cinema", 45.0)
        res = self.db.update_expense(add["id"], "Lazer", "Cinema IMAX", 60.0)
        self.assertTrue(res["success"])
        fetched = self.db.get_expense(add["id"])
        self.assertEqual(fetched["data"]["description"], "Cinema IMAX")
        self.assertEqual(fetched["data"]["amount"], 60.0)

    def test_update_expense_not_found(self):
        res = self.db.update_expense(9999, "X", "Y", 1.0)
        self.assertFalse(res["success"])
        self.assertIn("nao encontrada", res["message"].lower())

    def test_update_expense_strips_whitespace(self):
        add = self.db.add_expense("A", "B", 1.0)
        self.db.update_expense(add["id"], "  NovaCat  ", "  NovaDesc  ", 99.0)
        fetched = self.db.get_expense(add["id"])
        self.assertEqual(fetched["data"]["category"], "NovaCat")
        self.assertEqual(fetched["data"]["description"], "NovaDesc")

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------
    def test_delete_expense_success(self):
        add = self.db.add_expense("Saude", "Farmacia", 35.0)
        res = self.db.delete_expense(add["id"])
        self.assertTrue(res["success"])
        fetched = self.db.get_expense(add["id"])
        self.assertFalse(fetched["success"])

    def test_delete_expense_not_found(self):
        res = self.db.delete_expense(9999)
        self.assertFalse(res["success"])
        self.assertIn("nao encontrada", res["message"].lower())


class TestDatabaseAggregation(unittest.TestCase):
    """Testa agregacoes mensais e drill-down."""

    def setUp(self):
        self.db = Database(db_path=":memory:")
        # Inserir dados de dois meses distintos
        self.db.add_expense("Alimentacao", "Mercado", 300.0)
        self.db.add_expense("Alimentacao", "Padaria", 50.0)
        self.db.add_expense("Transporte", "Uber", 100.0)
        self.db.add_expense("Transporte", "Onibus", 50.0)
        # Datas futuras nao controlamos diretamente, mas como usamos
        # datetime('now') no DEFAULT, todos ficam no mes atual.

    def test_get_months_summary_returns_current_month(self):
        res = self.db.get_months_summary()
        self.assertTrue(res["success"])
        self.assertEqual(len(res["data"]), 1)
        self.assertEqual(res["data"][0]["count"], 4)
        self.assertEqual(res["data"][0]["total"], 500.0)

    def test_get_categories_by_month(self):
        from datetime import datetime
        month = datetime.now().strftime("%Y-%m")
        res = self.db.get_categories_by_month(month)
        self.assertTrue(res["success"])
        self.assertEqual(len(res["data"]), 2)
        # Ordenado por total DESC: Alimentacao (350) > Transporte (150)
        self.assertEqual(res["data"][0]["category"], "Alimentacao")
        self.assertEqual(res["data"][0]["total"], 350.0)
        self.assertEqual(res["data"][1]["category"], "Transporte")
        self.assertEqual(res["data"][1]["total"], 150.0)

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


class TestDatabaseBulk(unittest.TestCase):
    """Testa cadastro em massa."""

    def setUp(self):
        self.db = Database(db_path=":memory:")

    def test_bulk_insert_success(self):
        lines = "Mercado Extra, 150.50\nPadaria, 12.30\nFarmacia, 45.00"
        res = self.db.add_expenses_bulk("Alimentacao", lines)
        self.assertTrue(res["success"])
        self.assertEqual(res["inserted"], 3)
        self.assertEqual(len(res["errors"]), 0)

    def test_bulk_insert_with_comma_decimal(self):
        lines = "Pao, 5,50\nLeite, 8,30"
        res = self.db.add_expenses_bulk("Alimentacao", lines)
        self.assertTrue(res["success"])
        self.assertEqual(res["inserted"], 2)

    def test_bulk_insert_with_currency_symbol(self):
        lines = "Supermercado, R$ 200.00\nGasolina, $ 150.00"
        res = self.db.add_expenses_bulk("Diversos", lines)
        self.assertTrue(res["success"])
        self.assertEqual(res["inserted"], 2)

    def test_bulk_insert_invalid_line(self):
        lines = "Valido, 10.00\nLinhaInvalidaSemVirgula\nOutro, 20.00"
        res = self.db.add_expenses_bulk("Teste", lines)
        self.assertTrue(res["success"])
        self.assertEqual(res["inserted"], 2)
        self.assertEqual(len(res["errors"]), 1)
        self.assertIn("Formato invalido", res["errors"][0])

    def test_bulk_insert_invalid_value(self):
        lines = "Teste, abc"
        res = self.db.add_expenses_bulk("Teste", lines)
        self.assertTrue(res["success"])
        self.assertEqual(res["inserted"], 0)
        self.assertEqual(len(res["errors"]), 1)
        self.assertIn("Valor invalido", res["errors"][0])

    def test_bulk_insert_empty_lines_ignored(self):
        lines = "\n\nItem1, 10.00\n\nItem2, 20.00\n\n"
        res = self.db.add_expenses_bulk("Teste", lines)
        self.assertTrue(res["success"])
        self.assertEqual(res["inserted"], 2)


class TestDatabaseRawParser(unittest.TestCase):
    """Testa o parser de texto bruto / notificacoes."""

    def setUp(self):
        self.db = Database(db_path=":memory:")

    def test_parse_simple_comma_format(self):
        text = "Supermercado, 150.50"
        res = self.db.parse_raw_text(text)
        self.assertTrue(res["success"])
        self.assertEqual(len(res["parsed"]), 1)
        self.assertEqual(res["parsed"][0]["description"], "Supermercado")
        self.assertEqual(res["parsed"][0]["amount"], 150.50)

    def test_parse_notification_style(self):
        text = "Compra no Supermercado valor R$ 150,50"
        res = self.db.parse_raw_text(text)
        self.assertTrue(res["success"])
        self.assertEqual(len(res["parsed"]), 1)
        self.assertEqual(res["parsed"][0]["amount"], 150.50)
        # Descricao deve ter sido limpa dos prefixos
        self.assertIn("Supermercado", res["parsed"][0]["description"])

    def test_parse_payment_style(self):
        text = "Pagamento de R$ 45,00 para Uber"
        res = self.db.parse_raw_text(text)
        self.assertTrue(res["success"])
        self.assertEqual(len(res["parsed"]), 1)
        self.assertEqual(res["parsed"][0]["amount"], 45.0)

    def test_parse_multiple_lines(self):
        text = "Mercado, 100.00\nUber, 25.50\nCinema, 60.00"
        res = self.db.parse_raw_text(text)
        self.assertTrue(res["success"])
        self.assertEqual(len(res["parsed"]), 3)

    def test_parse_no_value_found(self):
        text = "Apenas uma descricao sem valor"
        res = self.db.parse_raw_text(text)
        self.assertFalse(res["success"])
        self.assertEqual(len(res["parsed"]), 0)
        self.assertEqual(len(res["errors"]), 1)

    def test_parse_mixed_valid_invalid(self):
        text = "Valido, 10.00\nSem valor aqui\nOutro, 20.00"
        res = self.db.parse_raw_text(text)
        self.assertTrue(res["success"])
        self.assertEqual(len(res["parsed"]), 2)
        self.assertEqual(len(res["errors"]), 1)

    def test_save_parsed_expenses(self):
        parsed = [
            {"description": "Teste A", "amount": 10.0},
            {"description": "Teste B", "amount": 20.0},
        ]
        res = self.db.save_parsed_expenses("CategoriaX", parsed)
        self.assertTrue(res["success"])
        self.assertEqual(res["inserted"], 2)

    def test_save_parsed_expenses_skips_invalid(self):
        parsed = [
            {"description": "Valido", "amount": 10.0},
            {"description": "", "amount": 5.0},       # sem descricao
            {"description": "Zero", "amount": 0.0},   # valor zero
            {"description": "Negativo", "amount": -1}, # valor negativo
        ]
        res = self.db.save_parsed_expenses("Cat", parsed)
        self.assertTrue(res["success"])
        self.assertEqual(res["inserted"], 1)
        self.assertEqual(len(res["errors"]), 3)


class TestDatabaseEdgeCases(unittest.TestCase):
    """Testa casos de borda e robustez."""

    def setUp(self):
        self.db = Database(db_path=":memory:")

    def test_very_long_description(self):
        long_desc = "A" * 1000
        res = self.db.add_expense("Teste", long_desc, 1.0)
        self.assertTrue(res["success"])
        fetched = self.db.get_expense(res["id"])
        self.assertEqual(fetched["data"]["description"], long_desc)

    def test_special_characters_in_category(self):
        res = self.db.add_expense("Cafe & Lanche", "Pao de queijo", 5.0)
        self.assertTrue(res["success"])
        fetched = self.db.get_expense(res["id"])
        self.assertEqual(fetched["data"]["category"], "Cafe & Lanche")

    def test_unicode_characters(self):
        res = self.db.add_expense("Alimentação", "Pão de queijo ☕", 5.0)
        self.assertTrue(res["success"])
        fetched = self.db.get_expense(res["id"])
        self.assertEqual(fetched["data"]["description"], "Pão de queijo ☕")

    def test_float_precision(self):
        res = self.db.add_expense("Teste", "Precisao", 10.99)
        self.assertTrue(res["success"])
        fetched = self.db.get_expense(res["id"])
        self.assertAlmostEqual(fetched["data"]["amount"], 10.99, places=2)

    def test_database_file_created(self):
        """Testa criacao com arquivo real (nao :memory:)."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            db = Database(db_path=path)
            res = db.add_expense("Teste", "Arquivo", 1.0)
            self.assertTrue(res["success"])
            self.assertTrue(os.path.exists(path))
        finally:
            os.unlink(path)


# =============================================================================
# TESTES DA API (app.py)
# =============================================================================
# Mock do modulo webview (nao instalado no ambiente de teste)
import types
if "webview" not in sys.modules:
    sys.modules["webview"] = types.ModuleType("webview")

from app import Api


# =============================================================================
# TESTES DA API (app.py)
# =============================================================================
class TestApiBridge(unittest.TestCase):
    """Testa a classe Api que expoe metodos ao JavaScript."""

    def setUp(self):
        """Cria uma instancia da Api com um DB em memoria."""
        self.api = Api()
        # Substituimos o db interno por um em memoria
        self.api.db = Database(db_path=":memory:")

    def test_api_add_expense(self):
        res = self.api.add_expense("Alimentacao", "Teste", 50.0)
        self.assertTrue(res["success"])
        self.assertIn("id", res)

    def test_api_get_months_summary_empty(self):
        res = self.api.get_months_summary()
        self.assertTrue(res["success"])
        self.assertEqual(res["data"], [])

    def test_api_get_months_summary_with_data(self):
        self.api.add_expense("A", "B", 100.0)
        res = self.api.get_months_summary()
        self.assertTrue(res["success"])
        self.assertEqual(len(res["data"]), 1)
        self.assertEqual(res["data"][0]["total"], 100.0)

    def test_api_update_expense(self):
        add = self.api.add_expense("Cat", "Desc", 10.0)
        res = self.api.update_expense(add["id"], "NovaCat", "NovaDesc", 99.0)
        self.assertTrue(res["success"])
        fetched = self.api.get_expense(add["id"])
        self.assertEqual(fetched["data"]["category"], "NovaCat")

    def test_api_delete_expense(self):
        add = self.api.add_expense("Cat", "Desc", 10.0)
        res = self.api.delete_expense(add["id"])
        self.assertTrue(res["success"])
        fetched = self.api.get_expense(add["id"])
        self.assertFalse(fetched["success"])

    def test_api_parse_raw_text(self):
        res = self.api.parse_raw_text("Mercado, 100.00")
        self.assertTrue(res["success"])
        self.assertEqual(len(res["parsed"]), 1)
        self.assertEqual(res["parsed"][0]["amount"], 100.0)

    def test_api_save_parsed_expenses(self):
        parsed = [{"description": "Auto", "amount": 50.0}]
        res = self.api.save_parsed_expenses("Transporte", parsed)
        self.assertTrue(res["success"])
        self.assertEqual(res["inserted"], 1)

    def test_api_get_all_categories(self):
        self.api.add_expense("A", "B", 1.0)
        self.api.add_expense("A", "C", 2.0)
        self.api.add_expense("B", "D", 3.0)
        res = self.api.get_all_categories()
        self.assertTrue(res["success"])
        self.assertEqual(res["data"], ["A", "B"])

    def test_api_drill_down_flow(self):
        """Testa o fluxo completo de drill-down."""
        self.api.add_expense("Alimentacao", "Mercado", 200.0)
        self.api.add_expense("Alimentacao", "Padaria", 50.0)
        self.api.add_expense("Transporte", "Uber", 100.0)

        # Meses
        months = self.api.get_months_summary()
        self.assertTrue(months["success"])
        month_key = months["data"][0]["month"]

        # Categorias do mes
        cats = self.api.get_categories_by_month(month_key)
        self.assertTrue(cats["success"])
        self.assertEqual(len(cats["data"]), 2)

        # Despesas da categoria
        exps = self.api.get_expenses_by_month_and_category(month_key, "Alimentacao")
        self.assertTrue(exps["success"])
        self.assertEqual(len(exps["data"]), 2)

    def test_api_bulk_insert(self):
        lines = "Item1, 10.00\nItem2, 20.00"
        res = self.api.add_expenses_bulk("Teste", lines)
        self.assertTrue(res["success"])
        self.assertEqual(res["inserted"], 2)


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    # Usa TextTestRunner com verbosity 2 para output detalhado
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseCRUD))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseAggregation))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseBulk))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseRawParser))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestApiBridge))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit code nao-zero se houver falhas
    sys.exit(0 if result.wasSuccessful() else 1)
