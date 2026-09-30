"""
tests/test_measure_units.py - Peso/volume opcional com unidade (kg, g, ml, L): só anotação, nunca entra em conta.
"""

import unittest
from decimal import Decimal
from database import Database
from services.finance import FinanceService


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
        for blank in ("", "   ", None):
            _, row = self._add(blank, "L")
            self.assertIsNone(row["measure_value"])
            self.assertIsNone(row["measure_unit"])

    def test_comma_decimal_is_accepted(self):
        _, row = self._add("1,5", "L")
        self.assertEqual(row["measure_value"], Decimal("1.500"))

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
