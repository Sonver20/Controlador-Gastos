#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests.py - Testes automatizados para toda a logica do Controlador de Gastos.

Execute com:
    python3 tests.py -v
    python3 tests.py          # modo silencioso, so mostra falhas

NOTA SOBRE OS VALORES MONETARIOS NOS TESTES
--------------------------------------------
`Database` (database.py), `FinanceService` e `SchedulerService`
(services/) trabalham e retornam `decimal.Decimal` diretamente, entao os
testes que usam `self.db`/`self.finance`/`self.scheduler` comparam contra
`Decimal("X.XX")`.

`Api` (app.py) e a ponte com o JavaScript: ela converte todo `Decimal` em
string antes de retornar (pywebview serializa a resposta como JSON, que
nao sabe lidar com Decimal). Por isso, os testes que usam `self.api`
comparam os valores monetarios contra strings como "X.XX".
"""

import unittest
import os
import sys
import sqlite3
import tempfile
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

# Garante que os modulos do projeto sejam importaveis
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Database
from services.decimal_utils import to_decimal, to_quantity
from services.finance import FinanceService, resolve_amount
from services.scheduler import SchedulerService
from services.payroll import calcular_ferias
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


# =============================================================================
# TESTES DO DATABASE (logica de negocio SQLite)
# =============================================================================
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
        with self.assertRaises(InvalidOperation):
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
        with self.assertRaises(InvalidOperation):
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

    def test_blank_weight_is_stored_as_none(self):
        res = self.finance.add_expense("Cat", "Item", quantity="2", unit_price="5", measure_value="  ")
        self.assertIsNone(self.db.get_expense(res["id"])["data"]["measure_value"])

    def test_weight_accepts_comma_decimal(self):
        res = self.finance.add_expense("Cat", "Item", quantity="1", unit_price="5", measure_value="1,5")
        self.assertEqual(self.db.get_expense(res["id"])["data"]["measure_value"], Decimal("1.500"))

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

    def test_update_expense_can_clear_weight(self):
        add = self.finance.add_expense("Cat", "Item", quantity="1", unit_price="5", measure_value="2")
        self.finance.update_expense(add["id"], "Cat", "Item", quantity="1", unit_price="5", measure_value="")
        self.assertIsNone(self.db.get_expense(add["id"])["data"]["measure_value"])

    def test_update_adjusts_balance_by_difference_when_switching_mode(self):
        self.finance.set_balance("100.00")
        add = self.finance.add_expense("Feira", "Laranja", quantity="4", unit_price="1.00")  # -4.00
        self.finance.update_expense(add["id"], "Feira", "Laranja", quantity="4", unit_price="2.95",
                                    is_variable_price=True)  # agora 2.95 -> devolve 1.05
        self.assertEqual(self.finance.get_balance()["balance"], Decimal("97.05"))

    def test_add_expenses_structured_mixes_modes_and_weights(self):
        products = [
            {"description": "Leite", "unit_price": "4.50", "quantity": "2"},  # normal: 9.00
            {"description": "Laranja", "unit_price": "2.95", "quantity": "4",
             "is_variable_price": True, "measure_value": "0.740"},  # 2.95 exato, 4 itens, 0,740 kg
            {"description": "Arroz", "unit_price": "25.00", "quantity": "3", "measure_value": "5"},  # normal: 75.00
        ]
        res = self.finance.add_expenses_structured("Feira", None, products)
        self.assertTrue(res["success"])
        self.assertEqual(res["inserted"], 3)
        self.assertEqual(res["total"], Decimal("86.95"))

        from datetime import datetime
        month = datetime.now().strftime("%Y-%m")
        exps = self.db.get_expenses_by_month_and_category(month, "Feira")
        by_name = {e["description"]: e for e in exps["data"]}
        self.assertEqual(by_name["Leite"]["amount"], Decimal("9.00"))
        self.assertIsNone(by_name["Leite"]["measure_value"])
        self.assertEqual(by_name["Laranja"]["amount"], Decimal("2.95"))
        self.assertEqual(by_name["Laranja"]["quantity"], Decimal("4.000"))
        self.assertEqual(by_name["Laranja"]["measure_value"], Decimal("0.740"))
        self.assertEqual(by_name["Laranja"]["is_variable_price"], 1)
        self.assertEqual(by_name["Arroz"]["amount"], Decimal("75.00"))
        self.assertEqual(by_name["Arroz"]["measure_value"], Decimal("5.000"))
        self.assertEqual(by_name["Arroz"]["is_variable_price"], 0)


class TestMeasureUnits(unittest.TestCase):
    """Peso/volume opcional com unidade (kg, g, ml, L): só anotação, sem conversão."""

    def setUp(self):
        self.db = Database(db_path=":memory:")
        self.finance = FinanceService(self.db)

    def _add(self, value, unit):
        res = self.finance.add_expense("Cat", "Item", quantity="1", unit_price="10.00",
                                       measure_value=value, measure_unit=unit)
        return res, (self.db.get_expense(res["id"])["data"] if res["success"] else None)

    def test_each_unit_is_stored_as_typed_without_conversion(self):
        for value, unit in [("740", "g"), ("1.5", "L"), ("500", "ml"), ("0.750", "kg")]:
            res, row = self._add(value, unit)
            self.assertTrue(res["success"], unit)
            self.assertEqual(row["measure_unit"], unit)
            self.assertEqual(row["measure_value"], Decimal(value).quantize(Decimal("0.001")))
            self.assertEqual(row["amount"], Decimal("10.00"))  # unidade nunca mexe no valor

    def test_unit_is_case_insensitive_and_canonicalized(self):
        _, row = self._add("2", "l")
        self.assertEqual(row["measure_unit"], "L")
        _, row = self._add("2", "KG")
        self.assertEqual(row["measure_unit"], "kg")
        _, row = self._add("2", "ML")
        self.assertEqual(row["measure_unit"], "ml")

    def test_missing_unit_defaults_to_kg(self):
        _, row = self._add("2", None)
        self.assertEqual(row["measure_unit"], "kg")
        _, row = self._add("2", "")
        self.assertEqual(row["measure_unit"], "kg")

    def test_invalid_unit_is_rejected(self):
        res, _ = self._add("2", "libras")
        self.assertFalse(res["success"])

    def test_non_positive_value_is_rejected(self):
        res, _ = self._add("0", "kg")
        self.assertFalse(res["success"])
        res, _ = self._add("-1", "g")
        self.assertFalse(res["success"])

    def test_unit_without_value_is_discarded(self):
        _, row = self._add("", "L")
        self.assertIsNone(row["measure_value"])
        self.assertIsNone(row["measure_unit"])

    def test_update_can_change_unit(self):
        res, _ = self._add("0.740", "kg")
        self.finance.update_expense(res["id"], "Cat", "Item", quantity="1", unit_price="10.00",
                                    measure_value="740", measure_unit="g")
        row = self.db.get_expense(res["id"])["data"]
        self.assertEqual((row["measure_value"], row["measure_unit"]), (Decimal("740.000"), "g"))

    def test_update_can_clear_measure_and_unit_together(self):
        res, _ = self._add("2", "L")
        self.finance.update_expense(res["id"], "Cat", "Item", quantity="1", unit_price="10.00", measure_value="")
        row = self.db.get_expense(res["id"])["data"]
        self.assertIsNone(row["measure_value"])
        self.assertIsNone(row["measure_unit"])

    def test_structured_products_carry_their_own_unit(self):
        products = [
            {"description": "Suco", "unit_price": "8.00", "quantity": "1", "measure_value": "1.5", "measure_unit": "L"},
            {"description": "Queijo", "unit_price": "9.00", "quantity": "1", "measure_value": "300", "measure_unit": "g"},
            {"description": "Pão", "unit_price": "5.00", "quantity": "1"},
        ]
        res = self.finance.add_expenses_structured("Feira", None, products)
        self.assertEqual(res["inserted"], 3)
        from datetime import datetime
        exps = self.db.get_expenses_by_month_and_category(datetime.now().strftime("%Y-%m"), "Feira")["data"]
        by_name = {e["description"]: e for e in exps}
        self.assertEqual(by_name["Suco"]["measure_unit"], "L")
        self.assertEqual(by_name["Queijo"]["measure_unit"], "g")
        self.assertIsNone(by_name["Pão"]["measure_unit"])


class TestMeasureMigrationFromWeightKg(unittest.TestCase):
    """Bancos da v3.3.1 tinham `weight_kg`; viram `measure_value` + unidade "kg"."""

    def setUp(self):
        import tempfile, os
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "v331.db")
        import sqlite3
        conn = sqlite3.connect(self.path)
        conn.execute("""CREATE TABLE expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL, subcategory TEXT,
            description TEXT NOT NULL, amount DECIMAL NOT NULL, quantity DECIMAL NOT NULL DEFAULT 1,
            unit_price DECIMAL, is_variable_price INTEGER NOT NULL DEFAULT 0, weight_kg DECIMAL,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')))""")
        conn.execute("INSERT INTO expenses (category, description, amount, quantity, unit_price, weight_kg, created_at) "
                     "VALUES ('Mercado','Picanha',60.00,1,60.00,0.750,'2026-09-10 12:00:00')")
        conn.execute("INSERT INTO expenses (category, description, amount, quantity, unit_price, created_at) "
                     "VALUES ('Mercado','Pão',5.00,1,5.00,'2026-09-11 08:00:00')")
        conn.commit(); conn.close()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_weight_kg_becomes_measure_value_in_kg(self):
        db = Database(db_path=self.path)
        with_weight = db.get_expense(1)["data"]
        without = db.get_expense(2)["data"]
        self.assertEqual(with_weight["measure_value"], Decimal("0.750"))
        self.assertEqual(with_weight["measure_unit"], "kg")
        self.assertIsNone(without["measure_value"])
        self.assertIsNone(without["measure_unit"])
        self.assertNotIn("weight_kg", with_weight)

    def test_migrated_expense_can_be_edited_with_another_unit(self):
        db = Database(db_path=self.path)
        FinanceService(db).update_expense(1, "Mercado", "Picanha", quantity="1", unit_price="60.00",
                                          measure_value="750", measure_unit="g")
        row = db.get_expense(1)["data"]
        self.assertEqual((row["measure_value"], row["measure_unit"]), (Decimal("750.000"), "g"))

    def test_migration_is_idempotent(self):
        Database(db_path=self.path)
        db = Database(db_path=self.path)  # abrir de novo não pode quebrar nem duplicar
        self.assertEqual(db.get_expense(1)["data"]["measure_unit"], "kg")


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
        self.db.insert_monthly_group("Contas", [
            {"category": "Mercado", "subcategory": None, "description": "Feira do mes",
             "quantity": Decimal("1"), "unit_price": Decimal("300.00")},
        ])
        self.finance.rename_category("Mercado", "Supermercado")
        groups = self.db.get_monthly_groups()
        self.assertEqual(groups[0]["items"][0]["category"], "Supermercado")

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
            __import__("datetime").datetime.now().strftime("%Y-%m"), "Acougue")["data"]}
        restaurante_subs = {r["subcategory"] for r in self.db.get_subcategories_by_month_and_category(
            __import__("datetime").datetime.now().strftime("%Y-%m"), "Restaurante")["data"]}
        self.assertIn("Bovinos", acougue_subs)
        self.assertIn("Carnes", restaurante_subs)

    def test_rename_subcategory_from_empty_bucket_assigns_name(self):
        self.finance.add_expense("Mercado", "Item avulso", "5.00")  # sem subcategoria
        res = self.finance.rename_subcategory("Mercado", "", "Diversos")
        self.assertTrue(res["success"])
        from datetime import datetime
        month = datetime.now().strftime("%Y-%m")
        exps = self.db.get_expenses_by_month_and_category(month, "Mercado", "Diversos")
        self.assertEqual(len(exps["data"]), 1)

    def test_rename_subcategory_to_empty_clears_it(self):
        self.finance.add_expense("Mercado", "Item", subcategory="Temp", amount="5.00")
        self.finance.rename_subcategory("Mercado", "Temp", "")
        from datetime import datetime
        month = datetime.now().strftime("%Y-%m")
        exps = self.db.get_expenses_by_month_and_category(month, "Mercado", "")
        self.assertEqual(len(exps["data"]), 1)


class TestSalaryCalendar(unittest.TestCase):
    """
    Testa a correcao do calendario de salario: em vez de assumir o mesmo
    dia do mes para todos os recebimentos, projeta a partir de uma data-
    ancora configuravel, avancando exatamente 30 dias por ciclo (o que faz
    o dia mudar de mes para mes, ja que nem todo mes tem o mesmo tamanho).
    """

    def setUp(self):
        self.db = Database(db_path=":memory:")
        self.finance = FinanceService(self.db)
        self.scheduler = SchedulerService(self.db)

    def test_set_next_salary_date_stores_anchor_30_days_before(self):
        res = self.scheduler.set_next_salary_date("2026-03-17")
        self.assertTrue(res["success"])
        salary = self.scheduler.get_salary()
        self.assertEqual(salary["last_salary_date"], "2026-02-15")

    def test_set_next_salary_date_invalid_format(self):
        res = self.scheduler.set_next_salary_date("17/03/2026")
        self.assertFalse(res["success"])

    def test_set_next_salary_date_preserves_balance_and_salary(self):
        self.finance.set_balance("1000.00")
        self.scheduler.set_salary("5000.00")
        self.scheduler.set_next_salary_date("2026-03-17")
        self.assertEqual(self.finance.get_balance()["balance"], Decimal("1000.00"))
        self.assertEqual(self.scheduler.get_salary()["salary"], Decimal("5000.00"))

    def test_calendar_without_reference_date(self):
        self.scheduler.set_salary("3000.00")
        cal = self.scheduler.get_salary_calendar(vacation_month=7)
        self.assertTrue(cal["success"])
        self.assertFalse(cal["has_reference_date"])
        self.assertEqual(cal["data"], [])

    def test_calendar_dates_are_exactly_30_days_apart(self):
        """O nucleo da correcao: cada data deve ser exatamente 30 dias
        apos a anterior, nao 'o mesmo dia do proximo mes'."""
        self.scheduler.set_salary("3000.00")
        self.scheduler.set_next_salary_date("2026-09-15")
        cal = self.scheduler.get_salary_calendar(vacation_month=1, count=6)
        self.assertTrue(cal["has_reference_date"])
        dates = [datetime.strptime(e["date"], "%Y-%m-%d") for e in cal["data"]]
        for i in range(1, len(dates)):
            self.assertEqual((dates[i] - dates[i - 1]).days, 30)

    def test_calendar_feb_to_march_drifts_correctly(self):
        """Caso especifico da reclamacao original: recebendo em 15/02, o
        proximo ciclo cai bem depois do dia 15 de marco (nao no mesmo dia).
        Usa uma data no futuro (2027) para nao ser adiantada para "hoje"
        pela logica de projecao (isso e testado separadamente em
        test_calendar_projects_forward_from_past_anchor)."""
        self.scheduler.set_salary("3000.00")
        self.scheduler.set_next_salary_date("2027-02-15")
        cal = self.scheduler.get_salary_calendar(vacation_month=1, count=2)
        first, second = cal["data"][0]["date"], cal["data"][1]["date"]
        self.assertEqual(first, "2027-02-15")
        # 15/02/2027 + 30 dias = 17/03/2027 (2027 nao e bissexto: fev tem 28 dias)
        self.assertEqual(second, "2027-03-17")

    def test_calendar_marks_vacation_month_with_net_amount(self):
        self.scheduler.set_salary("5000.00")
        self.scheduler.set_next_salary_date("2026-09-15")
        cal = self.scheduler.get_salary_calendar(vacation_month=10, count=3)
        vacation_entries = [e for e in cal["data"] if e["is_vacation"]]
        self.assertEqual(len(vacation_entries), 1)
        self.assertEqual(vacation_entries[0]["label"], "Férias (líquido)")
        # o valor liquido de ferias deve ser diferente do salario bruto
        self.assertNotEqual(vacation_entries[0]["amount"], Decimal("5000.00"))

    def test_calendar_no_salary_configured_shows_none_amount(self):
        self.scheduler.set_next_salary_date("2026-09-15")
        cal = self.scheduler.get_salary_calendar(vacation_month=7, count=2)
        for e in cal["data"]:
            self.assertIsNone(e["amount"])
            self.assertEqual(e["label"], "Não configurado")

    def test_calendar_projects_forward_from_past_anchor(self):
        """Se a ancora estiver no passado, a lista deve comecar na
        primeira ocorrencia igual ou posterior a hoje, nao no passado."""
        self.scheduler.set_salary("3000.00")
        self.scheduler.set_next_salary_date("2020-01-15")  # bem no passado
        cal = self.scheduler.get_salary_calendar(vacation_month=7, count=1)
        first_date = datetime.strptime(cal["data"][0]["date"], "%Y-%m-%d")
        self.assertGreaterEqual(first_date, datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))

    def test_calendar_future_next_date_beyond_30_days_shown_exactly(self):
        """Bug corrigido: se a 'proxima data de recebimento' configurada
        estiver a MAIS de 30 dias de hoje, o primeiro item do calendario
        tem que ser exatamente essa data -- e nao um ciclo (30 dias) antes
        dela. O erro acontecia porque a ancora interna (next_date - 30)
        ja caia no futuro e era exibida diretamente, sem avancar +30."""
        self.scheduler.set_salary("3000.00")
        far_future = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
        self.scheduler.set_next_salary_date(far_future)
        cal = self.scheduler.get_salary_calendar(vacation_month=1, count=1)
        self.assertEqual(cal["data"][0]["date"], far_future)


class TestAdditiveColumnMigration(unittest.TestCase):
    """
    Simula um banco ja no formato DECIMAL (versao anterior deste app, antes
    de subcategoria/quantidade/unit_price existirem) e confirma que as
    colunas novas sao adicionadas automaticamente, sem perder dados.
    """

    def setUp(self):
        import sqlite3
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        con = sqlite3.connect(self.path, detect_types=sqlite3.PARSE_DECLTYPES)
        con.execute(
            """CREATE TABLE expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                amount DECIMAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )"""
        )
        con.execute(
            """CREATE TABLE balance (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                amount DECIMAL NOT NULL DEFAULT 0,
                salary DECIMAL NOT NULL DEFAULT 0,
                last_salary_month TEXT,
                last_salary_date TEXT
            )"""
        )
        con.execute(
            "INSERT INTO expenses (category, description, amount) VALUES ('Mercado', 'Item Antigo', ?)",
            (Decimal("19.99"),),
        )
        con.commit()
        con.close()

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    def test_new_columns_added_and_backfilled(self):
        db = Database(db_path=self.path)
        from datetime import datetime
        month = datetime.now().strftime("%Y-%m")
        res = db.get_expenses_by_month_and_category(month, "Mercado")
        self.assertEqual(len(res["data"]), 1)
        row = res["data"][0]
        self.assertEqual(row["amount"], Decimal("19.99"))
        self.assertIn(row["quantity"], (Decimal("1"), Decimal("1.000")))
        self.assertEqual(row["unit_price"], Decimal("19.99"))
        self.assertIsNone(row["subcategory"])
        self.assertEqual(row["is_variable_price"], 0)
        self.assertIsNone(row["measure_value"])
        self.assertIsNone(row["measure_unit"])

    def test_new_inserts_work_after_additive_migration(self):
        db = Database(db_path=self.path)
        fin = FinanceService(db)
        res = fin.add_expense("Mercado", "Novo", subcategory="Bebidas", quantity="2", unit_price="3.00")
        self.assertTrue(res["success"])
        self.assertEqual(res["amount"], Decimal("6.00"))


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


# =============================================================================
# TESTES DO BALANCE / SALDO
# =============================================================================
class TestDatabaseBalance(unittest.TestCase):
    """Testa operacoes de saldo e subtracao."""

    def setUp(self):
        self.db = Database(db_path=":memory:")
        self.finance = FinanceService(self.db)
        self.scheduler = SchedulerService(self.db)

    def test_get_balance_default_zero(self):
        res = self.finance.get_balance()
        self.assertTrue(res["success"])
        self.assertEqual(res["balance"], Decimal("0"))

    def test_set_balance(self):
        res = self.finance.set_balance(1000.0)
        self.assertTrue(res["success"])
        self.assertEqual(res["balance"], Decimal("1000.00"))
        fetched = self.finance.get_balance()
        self.assertEqual(fetched["balance"], Decimal("1000.00"))

    def test_set_balance_overwrites(self):
        self.finance.set_balance(500.0)
        self.finance.set_balance(200.0)
        res = self.finance.get_balance()
        self.assertEqual(res["balance"], Decimal("200.00"))

    def test_subtract_from_balance(self):
        self.finance.set_balance(1000.0)
        res = self.finance.subtract_from_balance(150.50)
        self.assertTrue(res["success"])
        self.assertEqual(res["balance"], Decimal("849.50"))
        fetched = self.finance.get_balance()
        self.assertEqual(fetched["balance"], Decimal("849.50"))

    def test_subtract_from_balance_negative_result(self):
        self.finance.set_balance(50.0)
        res = self.finance.subtract_from_balance(100.0)
        self.assertTrue(res["success"])
        self.assertEqual(res["balance"], Decimal("-50.00"))

    def test_subtract_from_balance_no_prior_balance(self):
        res = self.finance.subtract_from_balance(100.0)
        self.assertTrue(res["success"])
        self.assertEqual(res["balance"], Decimal("-100.00"))

    def test_set_balance_preserves_salary(self):
        self.scheduler.set_salary(5000.0)
        self.finance.set_balance(1000.0)
        salary = self.scheduler.get_salary()
        self.assertEqual(salary["salary"], Decimal("5000.00"))

    def test_subtract_from_balance_preserves_salary(self):
        """Bug corrigido no refactor: subtract_from_balance usava
        INSERT OR REPLACE so com a coluna 'amount', o que zerava salario
        e datas de credito a cada despesa registrada."""
        self.scheduler.set_salary(5000.0)
        self.scheduler.set_last_salary_month("2026-01")
        self.finance.subtract_from_balance(100.0)
        salary = self.scheduler.get_salary()
        self.assertEqual(salary["salary"], Decimal("5000.00"))
        self.assertEqual(salary["last_salary_month"], "2026-01")

    def test_subtract_from_balance_no_float_drift_over_many_calls(self):
        """Muitas subtracoes de 0.10 nao devem acumular erro de float."""
        self.finance.set_balance("100.00")
        for _ in range(10):
            self.finance.subtract_from_balance("0.10")
        balance = self.finance.get_balance()
        self.assertEqual(balance["balance"], Decimal("99.00"))


# =============================================================================
# TESTES DO SALARIO
# =============================================================================
class TestDatabaseSalary(unittest.TestCase):
    """Testa operacoes de salario mensal."""

    def setUp(self):
        self.db = Database(db_path=":memory:")
        self.finance = FinanceService(self.db)
        self.scheduler = SchedulerService(self.db)

    def test_get_salary_default_zero(self):
        res = self.scheduler.get_salary()
        self.assertTrue(res["success"])
        self.assertEqual(res["salary"], Decimal("0"))
        self.assertIsNone(res["last_salary_month"])

    def test_set_salary(self):
        res = self.scheduler.set_salary(5000.0)
        self.assertTrue(res["success"])
        self.assertEqual(res["salary"], Decimal("5000.00"))
        fetched = self.scheduler.get_salary()
        self.assertEqual(fetched["salary"], Decimal("5000.00"))

    def test_set_salary_preserves_balance(self):
        self.finance.set_balance(1000.0)
        self.scheduler.set_salary(5000.0)
        balance = self.finance.get_balance()
        self.assertEqual(balance["balance"], Decimal("1000.00"))

    def test_add_salary_to_balance(self):
        self.finance.set_balance(1000.0)
        self.scheduler.set_salary(5000.0)
        res = self.scheduler.add_salary_to_balance()
        self.assertTrue(res["success"])
        self.assertEqual(res["balance"], Decimal("6000.00"))
        self.assertEqual(res["salary"], Decimal("5000.00"))

    def test_add_salary_to_balance_no_salary_configured(self):
        res = self.scheduler.add_salary_to_balance()
        self.assertFalse(res["success"])
        self.assertIn("não configurado", res["message"].lower())

    def test_add_salary_to_balance_zero_salary(self):
        self.scheduler.set_salary(0.0)
        res = self.scheduler.add_salary_to_balance()
        self.assertFalse(res["success"])

    def test_set_last_salary_month(self):
        # Precisa criar registro na tabela balance primeiro
        self.finance.set_balance(0.0)
        res = self.scheduler.set_last_salary_month("2026-08")
        self.assertTrue(res["success"])
        salary = self.scheduler.get_salary()
        self.assertEqual(salary["last_salary_month"], "2026-08")

    def test_add_salary_multiple_times(self):
        self.scheduler.set_salary(3000.0)
        self.scheduler.add_salary_to_balance()
        self.scheduler.add_salary_to_balance()
        balance = self.finance.get_balance()
        self.assertEqual(balance["balance"], Decimal("6000.00"))


# =============================================================================
# TESTES DE FERIAS (calculo com Decimal)
# =============================================================================
class TestCalcularFerias(unittest.TestCase):
    """Testa o calculo de ferias (INSS/IRRF) com decimal.Decimal."""

    def test_returns_decimal_values(self):
        res = calcular_ferias(5000.0)
        self.assertTrue(res["success"])
        for key in (
            "salario_bruto", "terco_constitucional", "total_bruto", "inss",
            "base_irrf", "irrf_calculado", "desconto_adicional",
            "irrf_final", "salario_liquido",
        ):
            self.assertIsInstance(res[key], Decimal)

    def test_salario_bruto_is_quantized_input(self):
        res = calcular_ferias("5000")
        self.assertEqual(res["salario_bruto"], Decimal("5000.00"))
        self.assertEqual(res["terco_constitucional"], Decimal("1666.67"))
        self.assertEqual(res["total_bruto"], Decimal("6666.67"))

    def test_salario_liquido_never_negative_logic(self):
        """Para um salario baixo, irrf_final nao deve deixar o liquido
        maior que o total bruto nem negativo."""
        res = calcular_ferias(1500.0)
        self.assertTrue(res["success"])
        self.assertGreaterEqual(res["salario_liquido"], Decimal("0"))
        self.assertLessEqual(res["salario_liquido"], res["total_bruto"])

    def test_invalid_input(self):
        res = calcular_ferias("abc")
        self.assertFalse(res["success"])


# =============================================================================
# TESTES DE MIGRACAO (bancos antigos com colunas REAL)
# =============================================================================
class TestLegacyFloatMigration(unittest.TestCase):
    """
    Simula um banco criado pela versao antiga do app (colunas REAL) e
    confirma que o Database novo migra automaticamente para DECIMAL sem
    perder ou distorcer os valores existentes.
    """

    def setUp(self):
        import sqlite3
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        con = sqlite3.connect(self.path)
        con.execute(
            """CREATE TABLE expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )"""
        )
        con.execute(
            """CREATE TABLE balance (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                amount REAL NOT NULL DEFAULT 0.0,
                salary REAL NOT NULL DEFAULT 0.0,
                last_salary_month TEXT,
                last_salary_date TEXT
            )"""
        )
        con.execute("INSERT INTO expenses (category, description, amount) VALUES ('Alimentacao','Mercado', 19.99)")
        con.execute("INSERT INTO expenses (category, description, amount) VALUES ('Transporte','Uber', 23.9)")
        con.execute(
            "INSERT OR REPLACE INTO balance (id, amount, salary, last_salary_month, last_salary_date) "
            "VALUES (1, 1234.56, 5000.0, '2026-08', '2026-08-01')"
        )
        con.commit()
        con.close()

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    def test_legacy_expenses_migrated_exactly(self):
        db = Database(db_path=self.path)
        cats = db.get_all_categories()
        self.assertEqual(cats["data"], ["Alimentacao", "Transporte"])

        months = db.get_months_summary()
        self.assertEqual(months["data"][0]["total"], Decimal("43.89"))

    def test_legacy_balance_and_salary_migrated_exactly(self):
        db = Database(db_path=self.path)
        fin = FinanceService(db)
        sched = SchedulerService(db)
        bal = fin.get_balance()
        sal = sched.get_salary()
        self.assertEqual(bal["balance"], Decimal("1234.56"))
        self.assertEqual(sal["salary"], Decimal("5000.00"))
        self.assertEqual(sal["last_salary_month"], "2026-08")
        self.assertEqual(sal["last_salary_date"], "2026-08-01")

    def test_new_inserts_after_migration_keep_incrementing_ids(self):
        db = Database(db_path=self.path)
        fin = FinanceService(db)
        res = fin.add_expense("Novo", "Item novo", "10.00")
        self.assertTrue(res["success"])
        self.assertGreater(res["id"], 2)

    def test_schema_is_decimal_after_migration(self):
        import sqlite3
        Database(db_path=self.path)  # dispara a migracao
        con = sqlite3.connect(self.path)
        cols = {row[1]: row[2] for row in con.execute("PRAGMA table_info(expenses)")}
        con.close()
        self.assertEqual(cols["amount"].upper(), "DECIMAL")
        self.assertIn("is_variable_price", cols)
        self.assertIn("measure_value", cols)
        self.assertIn("measure_unit", cols)


# =============================================================================
# TESTES DO to_decimal (helper de conversao)
# =============================================================================
class TestToDecimalHelper(unittest.TestCase):
    """Testa o helper central de conversao para Decimal."""

    def test_from_float_avoids_binary_noise(self):
        # Decimal(19.99) direto carregaria o ruido binario do float;
        # to_decimal deve produzir exatamente "19.99".
        self.assertEqual(to_decimal(19.99), Decimal("19.99"))

    def test_from_string(self):
        self.assertEqual(to_decimal("42.5"), Decimal("42.50"))

    def test_from_int(self):
        self.assertEqual(to_decimal(10), Decimal("10.00"))

    def test_from_decimal_passthrough(self):
        self.assertEqual(to_decimal(Decimal("7.777")), Decimal("7.78"))

    def test_rounds_half_up(self):
        self.assertEqual(to_decimal("10.995"), Decimal("11.00"))
        self.assertEqual(to_decimal("10.994"), Decimal("10.99"))

    def test_invalid_string_raises(self):
        with self.assertRaises(InvalidOperation):
            to_decimal("abc")

    def test_empty_string_raises(self):
        with self.assertRaises(InvalidOperation):
            to_decimal("")


# =============================================================================
# TESTES DO CONFIG
# =============================================================================
class TestConnectionRollback(unittest.TestCase):
    """
    Regressao para o _connection(): uma excecao no meio de uma operacao
    tem que dar rollback antes de liberar a conexao. Isso importa
    especialmente para :memory:, cuja conexao e persistente e reaproveitada
    entre chamadas -- sem o rollback, uma escrita nao commitada de uma
    chamada que falhou ficaria "pendurada" e seria commitada silenciosamente
    pela PROXIMA chamada bem-sucedida que reusar essa mesma conexao.
    """

    def test_memory_db_rolls_back_failed_write_before_next_call(self):
        db = Database(db_path=":memory:")

        with self.assertRaises(RuntimeError):
            with db._connection() as conn:
                conn.execute(
                    "INSERT INTO expenses (category, description, amount) VALUES (?, ?, ?)",
                    ("Categoria", "Nao deveria persistir", Decimal("999.00")),
                )
                raise RuntimeError("erro simulado no meio da transacao")

        # Uma operacao seguinte, totalmente independente e valida
        res = FinanceService(db).add_expense("Categoria", "Despesa valida", "5.00")
        self.assertTrue(res["success"])

        summary = db.get_months_summary()
        # So a despesa valida deve existir -- nao a de R$ 999 do erro
        self.assertEqual(summary["data"][0]["count"], 1)
        self.assertEqual(summary["data"][0]["total"], Decimal("5.00"))

    def test_file_db_rolls_back_failed_write(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            db = Database(db_path=path)
            with self.assertRaises(RuntimeError):
                with db._connection() as conn:
                    conn.execute(
                        "INSERT INTO expenses (category, description, amount) VALUES (?, ?, ?)",
                        ("Categoria", "Nao deveria persistir", Decimal("999.00")),
                    )
                    raise RuntimeError("erro simulado")

            # Reabre um Database novo apontando pro mesmo arquivo
            db2 = Database(db_path=path)
            summary = db2.get_months_summary()
            self.assertEqual(summary["data"], [])
        finally:
            os.unlink(path)

    def test_connection_context_manager_closes_file_connection(self):
        """Conexao de arquivo deve ser fechada ao sair do bloco `with`,
        mesmo no caminho de sucesso (sem excecao)."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            db = Database(db_path=path)
            with db._connection() as conn:
                pass
            with self.assertRaises(sqlite3.ProgrammingError):
                conn.execute("SELECT 1")  # conexao ja fechada
        finally:
            os.unlink(path)


class TestVersion(unittest.TestCase):
    """Garante que a versao segue o formato MAJOR.MINOR.PATCH do SemVer."""

    def test_version_format(self):
        from version import APP_VERSION
        parts = APP_VERSION.split(".")
        self.assertEqual(len(parts), 3, "versao deve seguir o formato MAJOR.MINOR.PATCH")
        for p in parts:
            self.assertTrue(p.isdigit(), f"'{p}' deveria ser numerico")


class TestConfig(unittest.TestCase):
    """Testa persistencia de configuracoes."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.tmpdir, "test_config.json")
        self.cfg = Config(config_path=self.config_path)

    def tearDown(self):
        if os.path.exists(self.config_path):
            os.unlink(self.config_path)
        os.rmdir(self.tmpdir)

    def test_theme_default(self):
        self.assertEqual(self.cfg.theme, "light")

    def test_set_theme(self):
        self.cfg.theme = "dark"
        # Recarrega do disco
        cfg2 = Config(config_path=self.config_path)
        self.assertEqual(cfg2.theme, "dark")

    def test_language_default(self):
        self.assertEqual(self.cfg.language, "pt")

    def test_set_language(self):
        self.cfg.language = "en"
        cfg2 = Config(config_path=self.config_path)
        self.assertEqual(cfg2.language, "en")

    def test_primary_color_default(self):
        self.assertEqual(self.cfg.primary_color, "violet")

    def test_set_primary_color_preset(self):
        self.cfg.primary_color = "blue"
        cfg2 = Config(config_path=self.config_path)
        self.assertEqual(cfg2.primary_color, "blue")

    def test_set_primary_color_custom_hex(self):
        self.cfg.primary_color = "#ff8800"
        cfg2 = Config(config_path=self.config_path)
        self.assertEqual(cfg2.primary_color, "#ff8800")

    def test_currency_default(self):
        self.assertEqual(self.cfg.currency, "BRL")

    def test_set_currency(self):
        self.cfg.currency = "USD"
        cfg2 = Config(config_path=self.config_path)
        self.assertEqual(cfg2.currency, "USD")

    def test_vacation_month_default(self):
        self.assertEqual(self.cfg.vacation_month, 7)

    def test_set_vacation_month(self):
        self.cfg.vacation_month = 12
        cfg2 = Config(config_path=self.config_path)
        self.assertEqual(cfg2.vacation_month, 12)

    def test_get_set_custom_key(self):
        self.cfg.set("custom_key", "custom_value")
        self.assertEqual(self.cfg.get("custom_key"), "custom_value")
        cfg2 = Config(config_path=self.config_path)
        self.assertEqual(cfg2.get("custom_key"), "custom_value")

    def test_get_missing_key_returns_default(self):
        self.assertIsNone(self.cfg.get("missing"))
        self.assertEqual(self.cfg.get("missing", "default"), "default")

    def test_persistence_survives_reinit(self):
        self.cfg.theme = "dark"
        self.cfg.set("language", "pt-BR")
        cfg2 = Config(config_path=self.config_path)
        self.assertEqual(cfg2.theme, "dark")
        self.assertEqual(cfg2.get("language"), "pt-BR")


# =============================================================================
# TESTES DA API (app.py)
# =============================================================================
# Mock do modulo webview (nao instalado no ambiente de teste)
import types
if "webview" not in sys.modules:
    sys.modules["webview"] = types.ModuleType("webview")

from app import Api
from config import Config


class TestApiBridge(unittest.TestCase):
    """
    Testa a classe Api que expoe metodos ao JavaScript.

    Os metodos monetarios sao decorados com @jsonify_result, entao os
    valores retornados aqui sao strings (ex.: "100.00"), nao Decimal --
    e exatamente o que atravessa a ponte pywebview -> JS de verdade.
    """

    def setUp(self):
        """Cria uma instancia da Api com um DB em memoria."""
        self.api = Api()
        # Substituimos o db interno por um em memoria, e os services
        # precisam ser recriados apontando para ele (senao continuariam
        # usando o banco de arquivo original criado em Api.__init__).
        self.api.db = Database(db_path=":memory:")
        self.api.finance = FinanceService(self.api.db)
        self.api.scheduler = SchedulerService(self.api.db)
        self.api.cfg = Config(config_path=os.path.join(tempfile.mkdtemp(), "cfg.json"))

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


# =============================================================================
# TESTES DE INTEGRACAO API + BALANCE
# =============================================================================
class TestApiBalanceIntegration(unittest.TestCase):
    """Testa que a API atualiza saldo ao registrar despesas."""

    def setUp(self):
        self.api = Api()
        self.api.db = Database(db_path=":memory:")
        self.api.finance = FinanceService(self.api.db)
        self.api.scheduler = SchedulerService(self.api.db)
        self.api.cfg = Config(config_path=os.path.join(tempfile.mkdtemp(), "cfg.json"))
        self.api.set_balance(1000.0)

    def test_api_add_expense_subtracts_balance(self):
        self.api.add_expense("Alimentacao", "Mercado", 150.0)
        balance = self.api.get_balance()
        self.assertEqual(balance["balance"], "850.00")

    def test_api_add_expense_multiple_subtracts_correctly(self):
        self.api.add_expense("A", "B", 100.0)
        self.api.add_expense("C", "D", 200.0)
        balance = self.api.get_balance()
        self.assertEqual(balance["balance"], "700.00")

    def test_api_bulk_insert_subtracts_total(self):
        lines = "Item1, 50.00\nItem2, 30.00"
        self.api.add_expenses_bulk("Teste", lines)
        balance = self.api.get_balance()
        self.assertEqual(balance["balance"], "920.00")

    def test_api_add_expense_zero_does_not_change_balance(self):
        initial = self.api.get_balance()["balance"]
        self.api.add_expense("X", "Y", 0.0)
        balance = self.api.get_balance()
        self.assertEqual(balance["balance"], initial)

    def test_api_delete_expense_restores_balance(self):
        """
        Mudanca de comportamento intencional (parte da reorganizacao para
        services/finance.py): excluir uma despesa agora DEVOLVE o valor
        dela ao saldo, para ficar consistente com editar (que ja ajusta o
        saldo pela diferenca). Antes, excluir nao mexia no saldo.
        """
        add = self.api.add_expense("Teste", "Teste", 100.0)
        balance_after_add = self.api.get_balance()["balance"]
        self.assertEqual(balance_after_add, "900.00")
        self.api.delete_expense(add["id"])
        balance_after_del = self.api.get_balance()["balance"]
        self.assertEqual(balance_after_del, "1000.00")

    def test_api_add_expense_preserves_salary(self):
        """Regressao do bug de subtract_from_balance zerando o salario."""
        self.api.set_salary(5000.0)
        self.api.add_expense("Teste", "Teste", 100.0)
        salary = self.api.get_salary()
        self.assertEqual(salary["salary"], "5000.00")

    def test_api_add_expense_quantity_mode_subtracts_computed_total(self):
        """No modo quantidade x preco unitario, o saldo deve ser
        descontado pelo valor CALCULADO (preco x qtd), nao por 'amount'
        (que nem e enviado pelo frontend nesse modo)."""
        res = self.api.add_expense(
            "Mercado", "Leite 1L", None, "Laticinios", "3", "4.50"
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["amount"], "13.50")
        balance = self.api.get_balance()
        self.assertEqual(balance["balance"], "986.50")

    def test_api_update_expense_increases_amount_decreases_balance(self):
        """Bug corrigido: editar uma despesa aumentando o preco nao
        atualizava o saldo. Agora a diferenca deve ser descontada."""
        add = self.api.add_expense("Mercado", "Item", "50.00")
        bal_after_add = self.api.get_balance()
        self.assertEqual(bal_after_add["balance"], "950.00")

        self.api.update_expense(add["id"], "Mercado", "Item", "80.00")  # +30
        bal_after_edit = self.api.get_balance()
        self.assertEqual(bal_after_edit["balance"], "920.00")

    def test_api_update_expense_decreases_amount_increases_balance(self):
        """Mesmo bug, sentido inverso: baixar o preco deve devolver a
        diferenca para o saldo."""
        add = self.api.add_expense("Mercado", "Item", "80.00")
        self.api.update_expense(add["id"], "Mercado", "Item", "20.00")  # -60
        balance = self.api.get_balance()
        self.assertEqual(balance["balance"], "980.00")

    def test_api_update_expense_via_quantity_change_adjusts_balance(self):
        """A edicao tambem cobre o caso de mudar so a quantidade (preco
        unitario igual), que muda o total calculado."""
        add = self.api.add_expense("Mercado", "Leite", None, None, "2", "4.50")  # 9.00 -> saldo 991.00
        self.api.update_expense(add["id"], "Mercado", "Leite", None, None, "4", "4.50")  # 18.00, +9
        balance = self.api.get_balance()
        self.assertEqual(balance["balance"], "982.00")

    def test_api_update_expense_no_amount_change_does_not_touch_balance(self):
        """Editar so a descricao/categoria (valor igual) nao deve mexer no saldo."""
        add = self.api.add_expense("Mercado", "Item", "50.00")
        bal_before = self.api.get_balance()["balance"]
        self.api.update_expense(add["id"], "Mercado", "Item renomeado", "50.00")
        bal_after = self.api.get_balance()["balance"]
        self.assertEqual(bal_before, bal_after)

    def test_api_add_expenses_structured_subtracts_total(self):
        """Nova Despesa unificada (lista de produtos) deve descontar o
        total exato da soma de todos os produtos inseridos."""
        res = self.api.add_expenses_structured("Alimentacao", "Assai Atacadista", [
            {"description": "Leite Integral 1L", "unit_price": "4.50", "quantity": "2"},
            {"description": "Picanha", "unit_price": "60.00", "quantity": "0.750"},
        ])
        self.assertTrue(res["success"])
        self.assertEqual(res["inserted"], 2)
        self.assertEqual(res["total"], "54.00")
        balance = self.api.get_balance()
        self.assertEqual(balance["balance"], "946.00")


# =============================================================================
# TESTES DE EDGE CASES ADICIONAIS
# =============================================================================
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


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    # Usa TextTestRunner com verbosity 2 para output detalhado
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseCRUD))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseAggregation))
    suite.addTests(loader.loadTestsFromTestCase(TestSubcategoryAndQuantity))
    suite.addTests(loader.loadTestsFromTestCase(TestVariablePriceExpense))
    suite.addTests(loader.loadTestsFromTestCase(TestMeasureUnits))
    suite.addTests(loader.loadTestsFromTestCase(TestMeasureMigrationFromWeightKg))
    suite.addTests(loader.loadTestsFromTestCase(TestCategoryRename))
    suite.addTests(loader.loadTestsFromTestCase(TestAdditiveColumnMigration))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseBulk))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseBalance))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseSalary))
    suite.addTests(loader.loadTestsFromTestCase(TestSalaryCalendar))
    suite.addTests(loader.loadTestsFromTestCase(TestCalcularFerias))
    suite.addTests(loader.loadTestsFromTestCase(TestConnectionRollback))
    suite.addTests(loader.loadTestsFromTestCase(TestLegacyFloatMigration))
    suite.addTests(loader.loadTestsFromTestCase(TestToDecimalHelper))
    suite.addTests(loader.loadTestsFromTestCase(TestVersion))
    suite.addTests(loader.loadTestsFromTestCase(TestConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestApiBridge))
    suite.addTests(loader.loadTestsFromTestCase(TestApiBalanceIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseAdditionalEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestMonthlyExpenses))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit code nao-zero se houver falhas
    sys.exit(0 if result.wasSuccessful() else 1)
