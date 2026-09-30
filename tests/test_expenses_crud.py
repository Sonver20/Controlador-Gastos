"""
tests/test_expenses_crud.py - CRUD de despesas (inserir, ler, atualizar, excluir) e cadastro em massa.
"""

import unittest
from decimal import Decimal
from database import Database
from services.finance import FinanceService


class TestDatabaseCRUD(unittest.TestCase):
    """Testa operacoes CRUD basicas."""

    def setUp(self):
        """Cria um banco em memoria para cada teste."""
        self.db = Database(db_path=":memory:")
        self.finance = FinanceService(self.db)

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------
    def test_add_expense_success(self):
        res = self.finance.add_expense("Alimentacao", "Mercado Extra", 150.50)
        self.assertTrue(res["success"])
        self.assertIsNotNone(res["id"])
        self.assertIn("sucesso", res["message"].lower())

    def test_add_expense_zero_amount(self):
        """Zero deve ser aceito (nao e negativo), mas e um edge case."""
        res = self.finance.add_expense("Teste", "Gratis", 0.0)
        self.assertTrue(res["success"])

    def test_add_expense_negative_amount(self):
        """A coluna DECIMAL aceita valores negativos; nossa logica nao bloqueia."""
        res = self.finance.add_expense("Teste", "Devolucao", -50.0)
        self.assertTrue(res["success"])

    def test_add_expense_strips_whitespace(self):
        res = self.finance.add_expense("  Alimentacao  ", "  Pao  ", 5.0)
        self.assertTrue(res["success"])
        fetched = self.db.get_expense(res["id"])
        self.assertEqual(fetched["data"]["category"], "Alimentacao")
        self.assertEqual(fetched["data"]["description"], "Pao")

    def test_add_expense_invalid_amount(self):
        """Um valor que nao da pra converter em Decimal deve falhar de forma limpa."""
        res = self.finance.add_expense("Teste", "Ruim", "abc")
        self.assertFalse(res["success"])
        self.assertIsNone(res["id"])

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------
    def test_get_expense_found(self):
        add = self.finance.add_expense("Transporte", "Uber", 23.90)
        res = self.db.get_expense(add["id"])
        self.assertTrue(res["success"])
        self.assertEqual(res["data"]["description"], "Uber")
        self.assertEqual(res["data"]["amount"], Decimal("23.90"))
        self.assertIsInstance(res["data"]["amount"], Decimal)

    def test_get_expense_not_found(self):
        res = self.db.get_expense(9999)
        self.assertFalse(res["success"])
        self.assertIsNone(res["data"])
        self.assertIn("não encontrada", res["message"].lower())

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------
    def test_update_expense_success(self):
        add = self.finance.add_expense("Lazer", "Cinema", 45.0)
        res = self.finance.update_expense(add["id"], "Lazer", "Cinema IMAX", 60.0)
        self.assertTrue(res["success"])
        fetched = self.db.get_expense(add["id"])
        self.assertEqual(fetched["data"]["description"], "Cinema IMAX")
        self.assertEqual(fetched["data"]["amount"], Decimal("60.00"))

    def test_update_expense_not_found(self):
        res = self.finance.update_expense(9999, "X", "Y", 1.0)
        self.assertFalse(res["success"])
        self.assertIn("não encontrada", res["message"].lower())

    def test_update_expense_strips_whitespace(self):
        add = self.finance.add_expense("A", "B", 1.0)
        self.finance.update_expense(add["id"], "  NovaCat  ", "  NovaDesc  ", 99.0)
        fetched = self.db.get_expense(add["id"])
        self.assertEqual(fetched["data"]["category"], "NovaCat")
        self.assertEqual(fetched["data"]["description"], "NovaDesc")

    def test_update_expense_invalid_amount(self):
        add = self.finance.add_expense("A", "B", 1.0)
        res = self.finance.update_expense(add["id"], "A", "B", "abc")
        self.assertFalse(res["success"])
        # o valor original nao deve ter sido alterado
        fetched = self.db.get_expense(add["id"])
        self.assertEqual(fetched["data"]["amount"], Decimal("1.00"))

    def test_update_expense_date(self):
        add = self.finance.add_expense("A", "B", 1.0)
        original = self.db.get_expense(add["id"])["data"]["created_at"]
        original_time = original.split(" ", 1)[1]

        res = self.finance.update_expense(add["id"], "A", "B", 1.0, date_str="2026-01-15")
        self.assertTrue(res["success"])
        fetched = self.db.get_expense(add["id"])
        self.assertEqual(fetched["data"]["created_at"], f"2026-01-15 {original_time}")

    def test_update_expense_invalid_date_format(self):
        add = self.finance.add_expense("A", "B", 1.0)
        res = self.finance.update_expense(add["id"], "A", "B", 1.0, date_str="15/01/2026")
        self.assertFalse(res["success"])
        # nao deve ter alterado nada
        fetched = self.db.get_expense(add["id"])
        self.assertEqual(fetched["data"]["description"], "B")

    def test_update_expense_without_date_str_keeps_original_date(self):
        add = self.finance.add_expense("A", "B", 1.0)
        original = self.db.get_expense(add["id"])["data"]["created_at"]
        self.finance.update_expense(add["id"], "A", "C", 2.0)  # sem date_str
        fetched = self.db.get_expense(add["id"])
        self.assertEqual(fetched["data"]["created_at"], original)

    def test_update_expense_date_not_found(self):
        res = self.finance.update_expense(9999, "A", "B", 1.0, date_str="2026-01-15")
        self.assertFalse(res["success"])

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------
    def test_delete_expense_success(self):
        add = self.finance.add_expense("Saude", "Farmacia", 35.0)
        res = self.finance.delete_expense(add["id"])
        self.assertTrue(res["success"])
        fetched = self.db.get_expense(add["id"])
        self.assertFalse(fetched["success"])

    def test_delete_expense_not_found(self):
        res = self.finance.delete_expense(9999)
        self.assertFalse(res["success"])
        self.assertIn("não encontrada", res["message"].lower())


class TestDatabaseBulk(unittest.TestCase):
    """Testa cadastro em massa."""

    def setUp(self):
        self.db = Database(db_path=":memory:")
        self.finance = FinanceService(self.db)

    def test_bulk_insert_success(self):
        lines = "Mercado Extra, 150.50\nPadaria, 12.30\nFarmacia, 45.00"
        res = self.finance.add_expenses_bulk("Alimentacao", lines)
        self.assertTrue(res["success"])
        self.assertEqual(res["inserted"], 3)
        self.assertEqual(len(res["errors"]), 0)
        self.assertEqual(res["total"], Decimal("207.80"))

    def test_bulk_insert_with_comma_decimal(self):
        # Bug corrigido: o parser usava rsplit(",", 1) (ultima virgula),
        # entao um valor em formato brasileiro como "5,50" era cortado no
        # lugar errado. Agora usa split(",", 1) (primeira virgula), que
        # trata tudo apos ela como o campo de valor.
        lines = "Pao, 5,50\nLeite, 8,30"
        res = self.finance.add_expenses_bulk("Alimentacao", lines)
        self.assertTrue(res["success"])
        self.assertEqual(res["inserted"], 2)
        self.assertEqual(res["total"], Decimal("13.80"))

    def test_bulk_insert_with_currency_symbol(self):
        lines = "Supermercado, R$ 200.00\nGasolina, $ 150.00"
        res = self.finance.add_expenses_bulk("Diversos", lines)
        self.assertTrue(res["success"])
        self.assertEqual(res["inserted"], 2)
        self.assertEqual(res["total"], Decimal("350.00"))

    def test_bulk_insert_invalid_line(self):
        lines = "Valido, 10.00\nLinhaInvalidaSemVirgula\nOutro, 20.00"
        res = self.finance.add_expenses_bulk("Teste", lines)
        self.assertTrue(res["success"])
        self.assertEqual(res["inserted"], 2)
        self.assertEqual(len(res["errors"]), 1)
        self.assertIn("Formato inválido", res["errors"][0])

    def test_bulk_insert_invalid_value(self):
        lines = "Teste, abc"
        res = self.finance.add_expenses_bulk("Teste", lines)
        self.assertTrue(res["success"])
        self.assertEqual(res["inserted"], 0)
        self.assertEqual(len(res["errors"]), 1)
        self.assertIn("Valor inválido", res["errors"][0])

    def test_bulk_insert_empty_lines_ignored(self):
        lines = "\n\nItem1, 10.00\n\nItem2, 20.00\n\n"
        res = self.finance.add_expenses_bulk("Teste", lines)
        self.assertTrue(res["success"])
        self.assertEqual(res["inserted"], 2)
