"""
tests/test_payroll.py - Cálculo de férias (1/3 constitucional, INSS e IRRF).
"""

import unittest
from decimal import Decimal
from services.payroll import calcular_ferias


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
