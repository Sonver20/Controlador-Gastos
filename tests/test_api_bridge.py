"""
tests/test_api_bridge.py - Api (app.py): a ponte entre o JavaScript e o backend.
"""

from tests.helpers import ApiTestCase


class TestApiBridge(ApiTestCase):
    """
    Testa a classe Api que expoe metodos ao JavaScript.

    Os metodos monetarios sao decorados com @jsonify_result, entao os
    valores retornados aqui sao strings (ex.: "100.00"), nao Decimal --
    e exatamente o que atravessa a ponte pywebview -> JS de verdade.
    """

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
        self.assertEqual(res["data"][0]["total"], "100.00")
        self.assertIsInstance(res["data"][0]["total"], str)

    def test_api_update_expense(self):
        add = self.api.add_expense("Cat", "Desc", 10.0)
        res = self.api.update_expense(add["id"], "NovaCat", "NovaDesc", 99.0)
        self.assertTrue(res["success"])
        fetched = self.api.get_expense(add["id"])
        self.assertEqual(fetched["data"]["category"], "NovaCat")
        self.assertEqual(fetched["data"]["amount"], "99.00")

    def test_api_update_expense_date(self):
        add = self.api.add_expense("Cat", "Desc", 10.0)
        res = self.api.update_expense(add["id"], "Cat", "Desc", 10.0, date_str="2026-03-01")
        self.assertTrue(res["success"])
        fetched = self.api.get_expense(add["id"])
        self.assertTrue(fetched["data"]["created_at"].startswith("2026-03-01"))

    def test_api_get_app_version(self):
        res = self.api.get_app_version()
        self.assertTrue(res["success"])
        # formato MAJOR.MINOR.PATCH
        parts = res["version"].split(".")
        self.assertEqual(len(parts), 3)
        for p in parts:
            self.assertTrue(p.isdigit())

    def test_api_delete_expense(self):
        add = self.api.add_expense("Cat", "Desc", 10.0)
        res = self.api.delete_expense(add["id"])
        self.assertTrue(res["success"])
        fetched = self.api.get_expense(add["id"])
        self.assertFalse(fetched["success"])

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
        self.assertEqual(res["total"], "30.00")

    def test_api_result_is_json_serializable(self):
        """Garante que nao sobra nenhum Decimal "vazando" para o JS
        (isso quebraria a chamada real do pywebview com um TypeError)."""
        import json
        self.api.add_expense("A", "B", 10.5)
        payload = self.api.get_months_summary()
        json.dumps(payload)  # nao deve levantar excecao
        payload2 = self.api.calcular_ferias("5000")
        json.dumps(payload2)

    def test_api_get_currency_default(self):
        res = self.api.get_currency()
        self.assertTrue(res["success"])
        self.assertEqual(res["currency"], "BRL")

    def test_api_set_currency(self):
        set_res = self.api.set_currency("USD")
        self.assertTrue(set_res["success"])
        self.assertEqual(self.api.get_currency()["currency"], "USD")

    def test_api_get_set_vacation_month(self):
        self.assertEqual(self.api.get_vacation_month()["month"], 7)
        set_res = self.api.set_vacation_month(12)
        self.assertTrue(set_res["success"])
        self.assertEqual(self.api.get_vacation_month()["month"], 12)

    def test_api_add_expense_variable_price_with_weight(self):
        res = self.api.add_expense("Feira", "Laranja", subcategory="Frutas",
                                    quantity="4", unit_price="2.95", is_variable_price=True, measure_value="0.740")
        self.assertTrue(res["success"])
        self.assertEqual(res["amount"], "2.95")
        fetched = self.api.get_expense(res["id"])["data"]
        self.assertEqual(fetched["measure_value"], "0.740")
        self.assertEqual(fetched["measure_unit"], "kg")
        self.assertEqual(fetched["quantity"], "4.000")

    def test_api_update_expense_weight(self):
        res = self.api.add_expense("Feira", "Arroz", quantity="3", unit_price="25.00")
        upd = self.api.update_expense(res["id"], "Feira", "Arroz", None, None, "3", "25.00", None, False, "5", "g")
        self.assertTrue(upd["success"])
        fetched = self.api.get_expense(res["id"])["data"]
        self.assertEqual(fetched["measure_value"], "5.000")
        self.assertEqual(fetched["measure_unit"], "g")

    def test_api_rename_category(self):
        self.api.add_expense("Mercado", "Item", "10.00")
        res = self.api.rename_category("Mercado", "Supermercado")
        self.assertTrue(res["success"])
        self.assertEqual(self.api.get_all_categories()["data"], ["Supermercado"])

    def test_api_rename_subcategory(self):
        self.api.add_expense("Acougue", "Picanha", subcategory="Carnes", unit_price="1", quantity="1")
        res = self.api.rename_subcategory("Acougue", "Carnes", "Bovinos")
        self.assertTrue(res["success"])
        self.assertEqual(self.api.get_all_subcategories()["data"], ["Bovinos"])
