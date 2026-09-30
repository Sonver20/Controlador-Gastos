"""
tests/test_connection.py - Conexão SQLite: rollback em caso de exceção no meio de uma transação.
"""

import unittest
import os
import sqlite3
import tempfile
from decimal import Decimal
from database import Database
from services.finance import FinanceService


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
