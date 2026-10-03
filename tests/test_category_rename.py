"""
tests/test_category_rename.py - Renomear categorias e subcategorias (global, também nas Despesas Mensais).
"""

import unittest
from decimal import Decimal
from database import Database
from services.finance import FinanceService
from tests.helpers import current_month


class TestCategoryRename(unittest.TestCase):
    """
    Testa renomear categorias e subcategorias (anotacoes.txt): deve valer
    para TODAS as despesas já lançadas (não só o mês sendo visto) e também
    para os templates de Despesa Mensal, já que é a mesma etiqueta de
    texto reaproveitada -- não uma entidade por mês.
    """

    def setUp(self):
        self.db = Database(db_path=":memory:")
        self.finance = FinanceService(self.db)

    def test_rename_category_updates_all_expenses(self):
        self.finance.add_expense("Mercado", "Item 1", "10.00")
        self.finance.add_expense("Mercado", "Item 2", "20.00")
        self.finance.add_expense("Farmacia", "Remedio", "15.00")

        res = self.finance.rename_category("Mercado", "Supermercado")
        self.assertTrue(res["success"])

        self.assertEqual(self.db.get_all_categories()["data"], ["Farmacia", "Supermercado"])

    def test_rename_category_updates_monthly_items_too(self):
        self.db.insert_monthly_group("Contas", "Mercado", None, [
            {"description": "Feira do mes", "quantity": Decimal("1"),
             "unit_price": Decimal("300.00")},
        ])
        self.finance.rename_category("Mercado", "Supermercado")
        groups = self.db.get_monthly_groups()
        self.assertEqual(groups[0]["category"], "Supermercado")

    def test_rename_category_empty_new_name_rejected(self):
        self.finance.add_expense("Mercado", "Item", "10.00")
        res = self.finance.rename_category("Mercado", "   ")
        self.assertFalse(res["success"])
        self.assertEqual(self.db.get_all_categories()["data"], ["Mercado"])

    def test_rename_subcategory_scoped_by_category(self):
        # Mesma subcategoria "Carnes" em duas categorias diferentes --
        # renomear dentro de uma não pode afetar a outra.
        self.finance.add_expense("Acougue", "Picanha", subcategory="Carnes", amount="45.00")
        self.finance.add_expense("Restaurante", "Prato", subcategory="Carnes", amount="30.00")

        self.finance.rename_subcategory("Acougue", "Carnes", "Bovinos")

        acougue_subs = {r["subcategory"] for r in self.db.get_subcategories_by_month_and_category(
            current_month(), "Acougue")["data"]}
        restaurante_subs = {r["subcategory"] for r in self.db.get_subcategories_by_month_and_category(
            current_month(), "Restaurante")["data"]}
        self.assertIn("Bovinos", acougue_subs)
        self.assertIn("Carnes", restaurante_subs)

    def test_rename_subcategory_from_empty_bucket_assigns_name(self):
        self.finance.add_expense("Mercado", "Item avulso", "5.00")  # sem subcategoria
        res = self.finance.rename_subcategory("Mercado", "", "Diversos")
        self.assertTrue(res["success"])
        month = current_month()
        exps = self.db.get_expenses_by_month_and_category(month, "Mercado", "Diversos")
        self.assertEqual(len(exps["data"]), 1)

    def test_rename_subcategory_to_empty_clears_it(self):
        self.finance.add_expense("Mercado", "Item", subcategory="Temp", amount="5.00")
        self.finance.rename_subcategory("Mercado", "Temp", "")
        month = current_month()
        exps = self.db.get_expenses_by_month_and_category(month, "Mercado", "")
        self.assertEqual(len(exps["data"]), 1)
