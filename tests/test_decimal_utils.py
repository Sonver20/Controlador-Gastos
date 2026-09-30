"""
tests/test_decimal_utils.py - Conversão para Decimal (to_decimal / to_quantity).
"""

import unittest
from decimal import Decimal
from services.decimal_utils import to_decimal


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
        with self.assertRaises(Exception):
            to_decimal("abc")

    def test_empty_string_raises(self):
        with self.assertRaises(Exception):
            to_decimal("")
