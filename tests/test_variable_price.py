"""
tests/test_variable_price.py - Modo "Peso variável": o valor vira o total pago e não multiplica pela quantidade.
"""

import unittest
from decimal import Decimal
from database import Database
from services.finance import FinanceService, resolve_amount
from tests.helpers import current_month


class TestVariablePriceExpense(unittest.TestCase):
    """
    Testa o modo "Peso variável" e o campo de peso (anotacoes.txt).

    Regras (as duas coisas são INDEPENDENTES):
    - `is_variable_price` só decide se o valor multiplica pela quantidade:
      desligado, a despesa funciona normalmente (preço x quantidade);
      ligado, o valor digitado já é o TOTAL pago e a quantidade (nº de
      itens) NÃO multiplica, mas continua sendo registrada.
    - `measure_value`/`measure_unit` (peso ou volume: kg, g, ml, L) são
      sempre opcionais e puramente informativos, em qualquer modo -- nunca
      entram em nenhuma conta.
    """

    def setUp(self):
        self.db = Database(db_path=":memory:")
        self.finance = FinanceService(self.db)

    def test_resolve_amount_variable_price_does_not_multiply(self):
        # 4 laranjas por R$2,95 no total -- NÃO é 2.95 * 4 = 11.80
        qty, price, amt = resolve_amount(None, "4", "2.95", is_variable_price=True)
        self.assertEqual(amt, Decimal("2.95"))
        self.assertEqual(qty, Decimal("4.000"))
        # preço "por item" é só informativo, derivado de total / quantidade
        self.assertEqual(price, Decimal("0.74"))  # 2.95 / 4 = 0.7375 -> 0.74

    def test_resolve_amount_normal_mode_still_multiplies(self):
        qty, price, amt = resolve_amount(None, "3", "25.00", is_variable_price=False)
        self.assertEqual(amt, Decimal("75.00"))

    def test_resolve_amount_variable_price_requires_total(self):
        with self.assertRaises(Exception):
            resolve_amount(None, "4", None, is_variable_price=True)

    def test_resolve_amount_variable_price_without_quantity_defaults_to_one(self):
        qty, price, amt = resolve_amount(None, None, "2.95", is_variable_price=True)
        self.assertEqual(qty, Decimal("1"))
        self.assertEqual(amt, Decimal("2.95"))
        self.assertEqual(price, Decimal("2.95"))

    def test_variable_price_keeps_item_count_and_weight_separate(self):
        # O exemplo do usuário: 4 laranjas, 740g no total, R$2,95 no total.
        res = self.finance.add_expense(
            "Feira", "Laranja", subcategory="Frutas",
            quantity="4", unit_price="2.95", is_variable_price=True, measure_value="0.740",
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["amount"], Decimal("2.95"))  # não multiplicou por 4
        fetched = self.db.get_expense(res["id"])["data"]
        self.assertEqual(fetched["amount"], Decimal("2.95"))
        self.assertEqual(fetched["quantity"], Decimal("4.000"))  # contagem preservada
        self.assertEqual(fetched["measure_value"], Decimal("0.740"))
        self.assertEqual(fetched["measure_unit"], "kg")  # sem unidade informada -> kg
        self.assertEqual(fetched["is_variable_price"], 1)

    def test_normal_mode_with_weight_annotation_still_multiplies(self):
        # "Três pacotes de arroz de 5kg": modo normal, peso é só anotação.
        res = self.finance.add_expense(
            "Mercado", "Arroz", quantity="3", unit_price="25.00", measure_value="5",
        )
        self.assertEqual(res["amount"], Decimal("75.00"))
        fetched = self.db.get_expense(res["id"])["data"]
        self.assertEqual(fetched["quantity"], Decimal("3.000"))
        self.assertEqual(fetched["measure_value"], Decimal("5.000"))
        self.assertEqual(fetched["is_variable_price"], 0)

    def test_weight_is_optional_and_defaults_to_none(self):
        res = self.finance.add_expense("Cat", "Item", "10.00")
        fetched = self.db.get_expense(res["id"])["data"]
        self.assertIsNone(fetched["measure_value"])
        self.assertEqual(fetched["is_variable_price"], 0)

    def test_update_expense_can_change_weight_and_mode(self):
        add = self.finance.add_expense("Feira", "Laranja", quantity="4", unit_price="1.00")  # normal: 4.00
        self.assertEqual(add["amount"], Decimal("4.00"))
        res = self.finance.update_expense(
            add["id"], "Feira", "Laranja", quantity="4", unit_price="2.95",
            is_variable_price=True, measure_value="0.740",
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["amount"], Decimal("2.95"))
        fetched = self.db.get_expense(add["id"])["data"]
        self.assertEqual(fetched["is_variable_price"], 1)
        self.assertEqual(fetched["quantity"], Decimal("4.000"))
        self.assertEqual(fetched["measure_value"], Decimal("0.740"))

    def test_update_adjusts_balance_by_difference_when_switching_mode(self):
        self.finance.set_balance("100.00")
        add = self.finance.add_expense("Feira", "Laranja", quantity="4", unit_price="1.00")  # -4.00
        self.finance.update_expense(add["id"], "Feira", "Laranja", quantity="4", unit_price="2.95",
                                    is_variable_price=True)  # agora 2.95 -> devolve 1.05
        self.assertEqual(self.finance.get_balance()["balance"], Decimal("97.05"))

    def test_add_expenses_structured_mixes_modes_and_weights(self):
        products = [
            {"description": "Leite", "unit_price": "4.50", "quantity": "2"},  # normal: 9.00
            {"description": "Laranja", "unit_price": "2.95", "quantity": "4", "is_variable_price": True,
             "measure_value": "740", "measure_unit": "g"},  # 2.95 exato, 4 itens, 740 g
            {"description": "Arroz", "unit_price": "25.00", "quantity": "3", "measure_value": "5"},  # normal: 75.00, 5 kg (unidade padrão)
        ]
        res = self.finance.add_expenses_structured("Feira", None, products)
        self.assertTrue(res["success"])
        self.assertEqual(res["inserted"], 3)
        self.assertEqual(res["total"], Decimal("86.95"))

        month = current_month()
        exps = self.db.get_expenses_by_month_and_category(month, "Feira")
        by_name = {e["description"]: e for e in exps["data"]}
        self.assertEqual(by_name["Leite"]["amount"], Decimal("9.00"))
        self.assertIsNone(by_name["Leite"]["measure_value"])
        self.assertEqual(by_name["Laranja"]["amount"], Decimal("2.95"))
        self.assertEqual(by_name["Laranja"]["quantity"], Decimal("4.000"))
        self.assertEqual(by_name["Laranja"]["measure_value"], Decimal("740.000"))
        self.assertEqual(by_name["Laranja"]["measure_unit"], "g")
        self.assertEqual(by_name["Laranja"]["is_variable_price"], 1)
        self.assertEqual(by_name["Arroz"]["amount"], Decimal("75.00"))
        self.assertEqual(by_name["Arroz"]["measure_value"], Decimal("5.000"))
        self.assertEqual(by_name["Arroz"]["measure_unit"], "kg")
        self.assertIsNone(by_name["Leite"]["measure_unit"])
        self.assertEqual(by_name["Arroz"]["is_variable_price"], 0)
