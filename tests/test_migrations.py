"""
tests/test_migrations.py - Migração automática de bancos criados por versões anteriores.
"""

import unittest
import os
import sqlite3
import tempfile
from datetime import datetime
from decimal import Decimal
from database import Database
from services.finance import FinanceService
from services.scheduler import SchedulerService


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
