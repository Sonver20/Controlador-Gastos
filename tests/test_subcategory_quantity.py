"""
tests/test_subcategory_quantity.py - Subcategorias e lançamento por preço unitário × quantidade (inclusive fracionária).
"""

import unittest
from datetime import datetime
from decimal import Decimal
from database import Database
from services.decimal_utils import to_quantity
from services.finance import FinanceService, resolve_amount


class TestSubcategoryAndQuantity(unittest.TestCase):
    """
    Testa as duas novidades pedidas em anotacoes.txt:
    1) subcategorias (ex.: Mercado > Laticinios, Acougue > Carnes)
    2) lancar despesa por preco unitario x quantidade, com o valor total
       calculado automaticamente pelo backend.
    """

    def setUp(self):
        self.db = Database(db_path=":memory:")
        self.finance = FinanceService(self.db)

    # ------------------------------------------------------------------
    # resolve_amount / to_quantity
    # ------------------------------------------------------------------
    def test_to_quantity_from_string_with_comma(self):
        self.assertEqual(to_quantity("0,750"), Decimal("0.750"))

    def test_to_quantity_from_float(self):
        self.assertEqual(to_quantity(2.0), Decimal("2.000"))

    def test_resolve_amount_simple_mode(self):
        qty, price, amt = resolve_amount("50.00", None, None)
        self.assertEqual(qty, Decimal("1"))
        self.assertEqual(price, Decimal("50.00"))
        self.assertEqual(amt, Decimal("50.00"))

    def test_resolve_amount_quantity_mode(self):
        qty, price, amt = resolve_amount(None, "3", "4.50")
        self.assertEqual(qty, Decimal("3.000"))
        self.assertEqual(price, Decimal("4.50"))
        self.assertEqual(amt, Decimal("13.50"))

    def test_resolve_amount_quantity_mode_zero_quantity_raises(self):
        with self.assertRaises(Exception):
            resolve_amount(None, "0", "10.00")

    # ------------------------------------------------------------------
    # add_expense com subcategoria
    # ------------------------------------------------------------------
    def test_add_expense_with_subcategory(self):
        res = self.finance.add_expense("Mercado", "Frango", "20.00", subcategory="Carnes")
        self.assertTrue(res["success"])
        fetched = self.db.get_expense(res["id"])
        self.assertEqual(fetched["data"]["subcategory"], "Carnes")

    def test_add_expense_without_subcategory_is_none(self):
        res = self.finance.add_expense("Mercado", "Item generico", "5.00")
        fetched = self.db.get_expense(res["id"])
        self.assertIsNone(fetched["data"]["subcategory"])

    def test_add_expense_blank_subcategory_normalizes_to_none(self):
        res = self.finance.add_expense("Mercado", "Item", "5.00", subcategory="   ")
        fetched = self.db.get_expense(res["id"])
        self.assertIsNone(fetched["data"]["subcategory"])

    # ------------------------------------------------------------------
    # add_expense com quantidade x preco unitario
    # ------------------------------------------------------------------
    def test_add_expense_quantity_mode_computes_amount(self):
        res = self.finance.add_expense(
            "Mercado", "Leite Integral 1L", subcategory="Laticinios", quantity="2", unit_price="4.50"
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["amount"], Decimal("9.00"))
        fetched = self.db.get_expense(res["id"])
        self.assertEqual(fetched["data"]["quantity"], Decimal("2.000"))
        self.assertEqual(fetched["data"]["unit_price"], Decimal("4.50"))
        self.assertEqual(fetched["data"]["amount"], Decimal("9.00"))

    def test_add_expense_quantity_mode_fractional_weight(self):
        """Ex.: 0.750 kg de picanha a R$ 60,00 o kg."""
        res = self.finance.add_expense("Acougue", "Picanha", subcategory="Carnes", quantity="0.750", unit_price="60.00")
        self.assertTrue(res["success"])
        self.assertEqual(res["amount"], Decimal("45.00"))

    def test_add_expense_default_quantity_is_one(self):
        """Modo simples (sem quantidade/preco unitario) grava quantidade=1."""
        res = self.finance.add_expense("Cat", "Item simples", "10.00")
        fetched = self.db.get_expense(res["id"])
        self.assertEqual(fetched["data"]["quantity"], Decimal("1"))
        self.assertEqual(fetched["data"]["unit_price"], Decimal("10.00"))

    def test_add_expense_quantity_mode_invalid_zero_quantity(self):
        res = self.finance.add_expense("Cat", "Item", quantity="0", unit_price="10.00")
        self.assertFalse(res["success"])

    def test_update_expense_switch_to_quantity_mode(self):
        add = self.finance.add_expense("Cat", "Item", "10.00")
        res = self.finance.update_expense(add["id"], "Cat", "Item", quantity="4", unit_price="2.50")
        self.assertTrue(res["success"])
        self.assertEqual(res["amount"], Decimal("10.00"))
        fetched = self.db.get_expense(add["id"])
        self.assertEqual(fetched["data"]["quantity"], Decimal("4.000"))
        self.assertEqual(fetched["data"]["unit_price"], Decimal("2.50"))

    # ------------------------------------------------------------------
    # Agregacao / drill-down por subcategoria
    # ------------------------------------------------------------------
    def test_get_subcategories_by_month_and_category(self):
        from datetime import datetime
        self.finance.add_expense("Acougue", "Picanha", subcategory="Carnes", quantity="1", unit_price="45.00")
        self.finance.add_expense("Acougue", "Frango", subcategory="Carnes", quantity="1", unit_price="20.00")
        self.finance.add_expense("Acougue", "Detergente", subcategory="Limpeza", quantity="1", unit_price="5.00")
        self.finance.add_expense("Acougue", "Sem sub", amount="3.00")

        month = datetime.now().strftime("%Y-%m")
        res = self.db.get_subcategories_by_month_and_category(month, "Acougue")
        self.assertTrue(res["success"])
        by_name = {row["subcategory"]: row for row in res["data"]}

        self.assertEqual(by_name["Carnes"]["total"], Decimal("65.00"))
        self.assertEqual(by_name["Carnes"]["count"], 2)
        self.assertEqual(by_name["Limpeza"]["total"], Decimal("5.00"))
        self.assertEqual(by_name[""]["total"], Decimal("3.00"))  # balde "sem subcategoria"

    def test_get_subcategories_when_none_used(self):
        """Categoria sem nenhuma subcategoria usada deve retornar so o balde vazio."""
        from datetime import datetime
        self.finance.add_expense("Transporte", "Uber", "20.00")
        self.finance.add_expense("Transporte", "Onibus", "5.00")
        month = datetime.now().strftime("%Y-%m")
        res = self.db.get_subcategories_by_month_and_category(month, "Transporte")
        self.assertEqual(len(res["data"]), 1)
        self.assertEqual(res["data"][0]["subcategory"], "")
        self.assertEqual(res["data"][0]["total"], Decimal("25.00"))

    def test_get_expenses_filtered_by_subcategory(self):
        from datetime import datetime
        self.finance.add_expense("Acougue", "Picanha", subcategory="Carnes", quantity="1", unit_price="45.00")
        self.finance.add_expense("Acougue", "Frango", subcategory="Carnes", quantity="1", unit_price="20.00")
        self.finance.add_expense("Acougue", "Sem sub", amount="3.00")
        month = datetime.now().strftime("%Y-%m")

        carnes = self.db.get_expenses_by_month_and_category(month, "Acougue", "Carnes")
        self.assertEqual(len(carnes["data"]), 2)

        sem_sub = self.db.get_expenses_by_month_and_category(month, "Acougue", "")
        self.assertEqual(len(sem_sub["data"]), 1)
        self.assertEqual(sem_sub["data"][0]["description"], "Sem sub")

        todos = self.db.get_expenses_by_month_and_category(month, "Acougue")
        self.assertEqual(len(todos["data"]), 3)

    def test_get_all_subcategories(self):
        self.finance.add_expense("Mercado", "A", subcategory="Bebidas", unit_price="1", quantity="1")
        self.finance.add_expense("Mercado", "B", subcategory="Bebidas", unit_price="1", quantity="1")
        self.finance.add_expense("Mercado", "C", subcategory="Laticinios", unit_price="1", quantity="1")
        self.finance.add_expense("Mercado", "D", amount="1.00")  # sem subcategoria
        res = self.db.get_all_subcategories()
        self.assertEqual(res["data"], ["Bebidas", "Laticinios"])

    # ------------------------------------------------------------------
    # add_expenses_structured (Nova Despesa unificada: lista de produtos)
    # ------------------------------------------------------------------
    def test_add_expenses_structured_basic(self):
        products = [
            {"description": "Leite Integral 1L", "unit_price": "4.50", "quantity": "2"},
            {"description": "Picanha", "unit_price": "60.00", "quantity": "0.750"},
        ]
        res = self.finance.add_expenses_structured("Alimentacao", "Assai Atacadista", products)
        self.assertTrue(res["success"])
        self.assertEqual(res["inserted"], 2)
        self.assertEqual(res["total"], Decimal("54.00"))

        from datetime import datetime
        month = datetime.now().strftime("%Y-%m")
        exps = self.db.get_expenses_by_month_and_category(month, "Alimentacao", "Assai Atacadista")
        by_name = {e["description"]: e for e in exps["data"]}
        self.assertEqual(by_name["Leite Integral 1L"]["amount"], Decimal("9.00"))
        self.assertEqual(by_name["Picanha"]["amount"], Decimal("45.00"))

    def test_add_expenses_structured_skips_invalid_products(self):
        products = [
            {"description": "Valido", "unit_price": "10.00", "quantity": "1"},
            {"description": "", "unit_price": "5.00", "quantity": "1"},        # sem nome
            {"description": "Sem preco", "unit_price": "", "quantity": "1"},   # sem preco
            {"description": "Qtd zero", "unit_price": "5.00", "quantity": "0"},  # qtd invalida
        ]
        res = self.finance.add_expenses_structured("Cat", None, products)
        self.assertTrue(res["success"])
        self.assertEqual(res["inserted"], 1)
        self.assertEqual(len(res["errors"]), 3)
        self.assertEqual(res["total"], Decimal("10.00"))

    def test_add_expenses_structured_shares_category_and_subcategory(self):
        products = [
            {"description": "A", "unit_price": "1.00", "quantity": "1"},
            {"description": "B", "unit_price": "2.00", "quantity": "1"},
        ]
        self.finance.add_expenses_structured("Mercado", "Padaria", products)
        from datetime import datetime
        month = datetime.now().strftime("%Y-%m")
        exps = self.db.get_expenses_by_month_and_category(month, "Mercado", "Padaria")
        self.assertEqual(len(exps["data"]), 2)
        for e in exps["data"]:
            self.assertEqual(e["category"], "Mercado")
            self.assertEqual(e["subcategory"], "Padaria")

    def test_add_expenses_structured_empty_list(self):
        res = self.finance.add_expenses_structured("Cat", None, [])
        self.assertTrue(res["success"])
        self.assertEqual(res["inserted"], 0)
        self.assertEqual(res["total"], Decimal("0"))
