"""
tests/test_api_balance.py - Api (app.py): integração com o saldo ao registrar despesas.
"""

from tests.helpers import ApiTestCase


class TestApiBalanceIntegration(ApiTestCase):
    """Testa que a API atualiza saldo ao registrar despesas."""

    def setUp(self):
        super().setUp()
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
