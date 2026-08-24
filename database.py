#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
database.py - SQLite helper class for Controlador de Gastos
Handles all CRUD operations, monthly aggregation, and category breakdown.

NOTA: Para bancos ':memory:', mantem uma conexao persistente aberta,
pois o SQLite destroi o banco em memoria quando a ultima conexao e fechada.
"""

import sqlite3
import os
import re
from typing import List, Dict, Any, Optional


class Database:
    """
    Clean SQLite helper. Para arquivos, usa conexoes novas a cada operacao
    (thread-safe). Para :memory:, mantem uma conexao persistente.
    Todos os metodos retornam dicts com 'success' para tratamento no JS.
    """

    def __init__(self, db_path: str = "gastos.db"):
        """
        Initialize database connection and ensure tables exist.
        Args:
            db_path: Path to the SQLite database file, or ':memory:' for tests.
        """
        self._is_memory = (db_path == ":memory:")
        self.db_path = db_path if self._is_memory else os.path.abspath(db_path)
        self._mem_conn: Optional[sqlite3.Connection] = None
        self._init_tables()
        self._migrate_tables()

    def _connect(self) -> sqlite3.Connection:
        """
        Retorna uma conexao com row_factory configurado.
        Para :memory:, reutiliza a conexao persistente.
        Para arquivos, cria uma nova conexao (thread-safe).
        """
        if self._is_memory:
            if self._mem_conn is None:
                self._mem_conn = sqlite3.connect(":memory:")
                self._mem_conn.row_factory = sqlite3.Row
            return self._mem_conn
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn

    def _init_tables(self) -> None:
        """Create the expenses and balance tables if they do not already exist."""
        try:
            conn = self._connect()
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS expenses (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    category    TEXT    NOT NULL,
                    description TEXT    NOT NULL,
                    amount      REAL    NOT NULL,
                    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS balance (
                    id              INTEGER PRIMARY KEY CHECK (id = 1),
                    amount          REAL NOT NULL DEFAULT 0.0,
                    salary          REAL NOT NULL DEFAULT 0.0,
                    last_salary_month TEXT
                )
                """
            )
            conn.commit()
            if not self._is_memory:
                conn.close()
        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to init tables: {e}")

    def _migrate_tables(self) -> None:
        """Adiciona colunas novas em tabelas existentes (migracao automatica)."""
        try:
            conn = self._connect()
            cursor = conn.execute("PRAGMA table_info(balance)")
            columns = [row["name"] for row in cursor.fetchall()]
            if "salary" not in columns:
                conn.execute("ALTER TABLE balance ADD COLUMN salary REAL NOT NULL DEFAULT 0.0")
            if "last_salary_month" not in columns:
                conn.execute("ALTER TABLE balance ADD COLUMN last_salary_month TEXT")
            conn.commit()
            if not self._is_memory:
                conn.close()
        except sqlite3.Error as e:
            print(f"[DB MIGRATE] {e}")

    def add_expense(self, category: str, description: str, amount: float) -> Dict[str, Any]:
        try:
            conn = self._connect()
            cursor = conn.execute(
                "INSERT INTO expenses (category, description, amount) VALUES (?, ?, ?)",
                (category.strip(), description.strip(), float(amount)),
            )
            conn.commit()
            last_id = cursor.lastrowid
            if not self._is_memory:
                conn.close()
            return {"success": True, "id": last_id, "message": "Despesa registrada com sucesso!"}
        except sqlite3.Error as e:
            return {"success": False, "id": None, "message": f"Erro ao salvar: {e}"}

    def add_expenses_bulk(self, category: str, lines: str) -> Dict[str, Any]:
        inserted = 0
        errors = []
        category = category.strip()
        try:
            conn = self._connect()
            for line in lines.strip().splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = [p.strip() for p in line.rsplit(",", 1)]
                if len(parts) != 2:
                    errors.append(f"Formato invalido: '{line}'")
                    continue
                desc, val_str = parts
                try:
                    val_str = val_str.replace("R$", "").replace("$", "").strip()
                    val_str = val_str.replace(",", ".")
                    amount = float(val_str)
                except ValueError:
                    errors.append(f"Valor invalido: '{val_str}'")
                    continue
                conn.execute(
                    "INSERT INTO expenses (category, description, amount) VALUES (?, ?, ?)",
                    (category, desc, amount),
                )
                inserted += 1
            conn.commit()
            if not self._is_memory:
                conn.close()
            msg = f"{inserted} despesa(s) inserida(s)."
            if errors:
                msg += f" {len(errors)} erro(s) encontrado(s)."
            return {"success": True, "inserted": inserted, "errors": errors, "message": msg}
        except sqlite3.Error as e:
            return {"success": False, "inserted": inserted, "errors": errors, "message": f"Erro em massa: {e}"}

    def get_expense(self, expense_id: int) -> Dict[str, Any]:
        try:
            conn = self._connect()
            row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
            if not self._is_memory:
                conn.close()
            if row:
                return {"success": True, "data": dict(row)}
            return {"success": False, "data": None, "message": "Despesa nao encontrada."}
        except sqlite3.Error as e:
            return {"success": False, "data": None, "message": str(e)}

    def update_expense(self, expense_id: int, category: str, description: str, amount: float) -> Dict[str, Any]:
        try:
            conn = self._connect()
            cursor = conn.execute(
                "UPDATE expenses SET category = ?, description = ?, amount = ? WHERE id = ?",
                (category.strip(), description.strip(), float(amount), expense_id),
            )
            conn.commit()
            rowcount = cursor.rowcount
            if not self._is_memory:
                conn.close()
            if rowcount == 0:
                return {"success": False, "message": "Despesa nao encontrada para atualizar."}
            return {"success": True, "message": "Despesa atualizada com sucesso!"}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Erro ao atualizar: {e}"}

    def delete_expense(self, expense_id: int) -> Dict[str, Any]:
        try:
            conn = self._connect()
            cursor = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
            conn.commit()
            rowcount = cursor.rowcount
            if not self._is_memory:
                conn.close()
            if rowcount == 0:
                return {"success": False, "message": "Despesa nao encontrada para excluir."}
            return {"success": True, "message": "Despesa excluida com sucesso!"}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Erro ao excluir: {e}"}

    # ------------------------------------------------------------------
    # Balance / Account
    # ------------------------------------------------------------------
    def get_balance(self) -> Dict[str, Any]:
        """Return current account balance."""
        try:
            conn = self._connect()
            row = conn.execute("SELECT amount FROM balance WHERE id = 1").fetchone()
            if not self._is_memory:
                conn.close()
            if row:
                return {"success": True, "balance": row["amount"]}
            return {"success": True, "balance": 0.0}
        except sqlite3.Error as e:
            return {"success": False, "balance": 0.0, "message": str(e)}

    def set_balance(self, amount: float) -> Dict[str, Any]:
        """Set account balance (overwrite), preserving salary."""
        try:
            conn = self._connect()
            row = conn.execute("SELECT salary, last_salary_month FROM balance WHERE id = 1").fetchone()
            salary = row["salary"] if row else 0.0
            last_month = row["last_salary_month"] if row else None
            conn.execute(
                "INSERT OR REPLACE INTO balance (id, amount, salary, last_salary_month) VALUES (1, ?, ?, ?)",
                (float(amount), salary, last_month)
            )
            conn.commit()
            if not self._is_memory:
                conn.close()
            return {"success": True, "balance": float(amount), "message": "Saldo atualizado."}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Erro ao atualizar saldo: {e}"}

    def get_salary(self) -> Dict[str, Any]:
        """Return configured monthly salary."""
        try:
            conn = self._connect()
            row = conn.execute("SELECT salary, last_salary_month FROM balance WHERE id = 1").fetchone()
            if not self._is_memory:
                conn.close()
            if row:
                return {"success": True, "salary": row["salary"], "last_salary_month": row["last_salary_month"]}
            return {"success": True, "salary": 0.0, "last_salary_month": None}
        except sqlite3.Error as e:
            return {"success": False, "salary": 0.0, "message": str(e)}

    def set_salary(self, amount: float) -> Dict[str, Any]:
        """Set monthly salary amount."""
        try:
            conn = self._connect()
            row = conn.execute("SELECT amount, last_salary_month FROM balance WHERE id = 1").fetchone()
            balance = row["amount"] if row else 0.0
            last_month = row["last_salary_month"] if row else None
            conn.execute(
                "INSERT OR REPLACE INTO balance (id, amount, salary, last_salary_month) VALUES (1, ?, ?, ?)",
                (balance, float(amount), last_month)
            )
            conn.commit()
            if not self._is_memory:
                conn.close()
            return {"success": True, "salary": float(amount), "message": "Salario configurado."}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Erro ao configurar salario: {e}"}

    def add_salary_to_balance(self) -> Dict[str, Any]:
        """Add monthly salary to current balance."""
        try:
            conn = self._connect()
            row = conn.execute("SELECT amount, salary FROM balance WHERE id = 1").fetchone()
            if not row or row["salary"] <= 0:
                if not self._is_memory:
                    conn.close()
                return {"success": False, "message": "Salario nao configurado."}
            current = row["amount"] if row["amount"] else 0.0
            salary = row["salary"]
            new_balance = current + salary
            conn.execute(
                "UPDATE balance SET amount = ? WHERE id = 1",
                (new_balance,)
            )
            conn.commit()
            if not self._is_memory:
                conn.close()
            return {"success": True, "balance": new_balance, "salary": salary, "message": f"Salario de R$ {salary:.2f} creditado."}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Erro ao creditar salario: {e}"}

    def set_last_salary_month(self, month: str) -> Dict[str, Any]:
        """Mark that salary was already credited for this month."""
        try:
            conn = self._connect()
            conn.execute("UPDATE balance SET last_salary_month = ? WHERE id = 1", (month,))
            conn.commit()
            if not self._is_memory:
                conn.close()
            return {"success": True}
        except sqlite3.Error as e:
            return {"success": False, "message": str(e)}

    def subtract_from_balance(self, amount: float) -> Dict[str, Any]:
        """Subtract expense amount from balance."""
        try:
            conn = self._connect()
            row = conn.execute("SELECT amount FROM balance WHERE id = 1").fetchone()
            current = row["amount"] if row else 0.0
            new_balance = current - float(amount)
            conn.execute(
                "INSERT OR REPLACE INTO balance (id, amount) VALUES (1, ?)",
                (new_balance,)
            )
            conn.commit()
            if not self._is_memory:
                conn.close()
            return {"success": True, "balance": new_balance, "message": f"Saldo: {new_balance:.2f}"}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Erro ao subtrair saldo: {e}"}

    def get_months_summary(self) -> Dict[str, Any]:
        try:
            conn = self._connect()
            rows = conn.execute(
                "SELECT strftime('%Y-%m', created_at) AS month, SUM(amount) AS total, COUNT(*) AS count "
                "FROM expenses GROUP BY month ORDER BY month DESC"
            ).fetchall()
            if not self._is_memory:
                conn.close()
            return {"success": True, "data": [dict(r) for r in rows]}
        except sqlite3.Error as e:
            return {"success": False, "data": [], "message": str(e)}

    def get_categories_by_month(self, month: str) -> Dict[str, Any]:
        try:
            conn = self._connect()
            rows = conn.execute(
                "SELECT category, SUM(amount) AS total, COUNT(*) AS count "
                "FROM expenses WHERE strftime('%Y-%m', created_at) = ? "
                "GROUP BY category ORDER BY total DESC", (month,)
            ).fetchall()
            if not self._is_memory:
                conn.close()
            return {"success": True, "data": [dict(r) for r in rows]}
        except sqlite3.Error as e:
            return {"success": False, "data": [], "message": str(e)}

    def get_expenses_by_month_and_category(self, month: str, category: str) -> Dict[str, Any]:
        try:
            conn = self._connect()
            rows = conn.execute(
                "SELECT id, category, description, amount, created_at "
                "FROM expenses WHERE strftime('%Y-%m', created_at) = ? AND category = ? "
                "ORDER BY created_at DESC", (month, category)
            ).fetchall()
            if not self._is_memory:
                conn.close()
            return {"success": True, "data": [dict(r) for r in rows]}
        except sqlite3.Error as e:
            return {"success": False, "data": [], "message": str(e)}

    def get_all_categories(self) -> Dict[str, Any]:
        try:
            conn = self._connect()
            rows = conn.execute("SELECT DISTINCT category FROM expenses ORDER BY category").fetchall()
            if not self._is_memory:
                conn.close()
            return {"success": True, "data": [r["category"] for r in rows]}
        except sqlite3.Error as e:
            return {"success": False, "data": [], "message": str(e)}

    def parse_raw_text(self, raw_text: str) -> Dict[str, Any]:
        results = []
        errors = []
        for line in raw_text.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            val_match = re.search(r"(?:R\$|\$)?\s*(\d+[.,]?\d{0,2})", line)
            if not val_match:
                errors.append(f"Valor nao encontrado em: '{line}'")
                continue
            val_str = val_match.group(1).replace(",", ".")
            try:
                amount = float(val_str)
            except ValueError:
                errors.append(f"Valor invalido em: '{line}'")
                continue
            desc = re.sub(r"^(Compra no|Pagamento de|Transferencia para|Pix para)\s*", "", line, flags=re.IGNORECASE)
            desc = re.sub(r"(?:R\$|\$)?\s*\d+[.,]?\d{0,2}", "", desc).strip()
            desc = re.sub(r"\b(valor|de|para|no|na)\b", "", desc, flags=re.IGNORECASE).strip()
            desc = re.sub(r"\s+", " ", desc).strip(", ")
            if not desc:
                desc = "Sem descricao"
            results.append({"description": desc, "amount": amount, "raw": line})
        return {
            "success": len(errors) == 0 or len(results) > 0,
            "parsed": results, "errors": errors,
            "message": f"{len(results)} item(ns) parseado(s), {len(errors)} erro(s).",
        }

    def save_parsed_expenses(self, category: str, parsed_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        inserted = 0
        errors = []
        category = category.strip()
        try:
            conn = self._connect()
            for item in parsed_list:
                desc = item.get("description", "").strip()
                amount = item.get("amount", 0)
                if not desc or amount <= 0:
                    errors.append(f"Dados invalidos: {item}")
                    continue
                conn.execute(
                    "INSERT INTO expenses (category, description, amount) VALUES (?, ?, ?)",
                    (category, desc, float(amount)),
                )
                inserted += 1
            conn.commit()
            if not self._is_memory:
                conn.close()
            return {"success": True, "inserted": inserted, "errors": errors, "message": f"{inserted} despesa(s) salva(s)."}
        except sqlite3.Error as e:
            return {"success": False, "inserted": inserted, "errors": errors, "message": str(e)}
