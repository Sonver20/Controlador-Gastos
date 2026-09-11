#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
database.py - SQLite helper class for Controlador de Gastos
Handles all CRUD operations, monthly aggregation, and category breakdown.

NOTA: Para bancos ':memory:', mantem uma conexao persistente aberta,
pois o SQLite destroi o banco em memoria quando a ultima conexao e fechada.

VALORES MONETARIOS
-------------------
Todo valor em dinheiro e representado internamente com `decimal.Decimal`
(nunca `float`), e persistido em colunas SQLite declaradas como `DECIMAL`.

O SQLite nao possui um tipo decimal nativo: colunas `NUMERIC`/`DECIMAL`
convertem automaticamente texto "bem formado" (ex.: "19.99") para o
storage class REAL (float de 64 bits) por causa da chamada "type affinity"
de colunas numericas. Para evitar isso, os valores Decimal sao adaptados
para `bytes` (UTF-8) antes de irem para o SQLite: um valor BLOB nao sofre
essa conversao automatica, entao o texto exato do Decimal e gravado sem
qualquer arredondamento binario. Um "converter" registrado faz o caminho
inverso ao ler, reconstruindo o Decimal a partir dos bytes.

Todas as agregacoes (somas por mes/categoria) sao feitas em Python com
Decimal, e nao via SQL SUM(), pois o SUM() do SQLite opera em ponto
flutuante internamente e reintroduziria os mesmos erros de arredondamento
que este refactor busca eliminar.
"""

import sqlite3
import os
import re
from contextlib import contextmanager
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import List, Dict, Any, Optional, Callable


# ==============================================================================
# Decimal <-> SQLite bridging
# ==============================================================================
TWO_PLACES = Decimal("0.01")
THREE_PLACES = Decimal("0.001")


def _parse_decimal(value: Any, places: Decimal, normalize_comma: bool) -> Decimal:
    """
    Nucleo compartilhado de to_decimal/to_quantity: converte str/int/float/
    Decimal em Decimal, arredondado para `places` casas decimais.

    Floats sao convertidos via `str(value)` antes de virar Decimal, para
    evitar herdar o "ruido" binario do float (ex.: Decimal(19.99) viraria
    19.988999999999999769..., enquanto Decimal(str(19.99)) vira exatamente
    "19.99"). `normalize_comma` decide se uma string tipo "5,50" deve virar
    "5.50" antes do parse -- usado por to_quantity, mas NAO por to_decimal
    (que espera "." como separador; chamadores que recebem virgula do
    usuario, como add_expenses_bulk, normalizam isso antes de chamar
    to_decimal). Levanta InvalidOperation/ValueError/TypeError para
    entradas invalidas, para que os chamadores possam tratar o erro.
    """
    if isinstance(value, Decimal):
        d = value
    elif isinstance(value, float):
        d = Decimal(str(value))
    elif isinstance(value, str):
        cleaned = value.strip()
        if normalize_comma:
            cleaned = cleaned.replace(",", ".")
        if cleaned == "":
            raise InvalidOperation("valor vazio")
        d = Decimal(cleaned)
    else:
        d = Decimal(value)
    return d.quantize(places, rounding=ROUND_HALF_UP)


def to_decimal(value: Any) -> Decimal:
    """Converte qualquer valor recebido (str, int, float, Decimal) em um
    Decimal arredondado para 2 casas decimais (centavos)."""
    return _parse_decimal(value, TWO_PLACES, normalize_comma=False)


def to_quantity(value: Any) -> Decimal:
    """Converte um valor de quantidade (pode ser fracionaria, ex.: peso em
    kg como '0.750') em Decimal com ate 3 casas decimais."""
    return _parse_decimal(value, THREE_PLACES, normalize_comma=True)


def _adapt_decimal(d: Decimal) -> bytes:
    """Adapta um Decimal para bytes (forca storage class BLOB no SQLite,
    imune a conversao automatica para REAL das colunas NUMERIC/DECIMAL)."""
    return format(d, "f").encode("utf-8")


def _convert_decimal(raw: bytes) -> Decimal:
    """Reconstroi um Decimal a partir dos bytes gravados no SQLite."""
    return Decimal(raw.decode("utf-8"))


sqlite3.register_adapter(Decimal, _adapt_decimal)
sqlite3.register_converter("DECIMAL", _convert_decimal)


def resolve_amount(amount: Any, quantity: Any, unit_price: Any):
    """
    Decide como calcular o valor final de uma despesa:
    - Se quantidade + preco unitario forem informados, o total e
      calculado como preco_unitario * quantidade (arredondado para 2
      casas decimais).
    - Caso contrario, usa o valor direto informado em `amount`, com
      quantidade implicita = 1 e preco unitario = o proprio valor.

    Retorna a tupla (quantity_decimal, unit_price_decimal, amount_decimal).
    Levanta InvalidOperation/ValueError/TypeError para entradas invalidas.
    """
    has_quantity = quantity is not None and str(quantity).strip() != ""
    has_unit_price = unit_price is not None and str(unit_price).strip() != ""
    if has_quantity and has_unit_price:
        qty = to_quantity(quantity)
        if qty <= 0:
            raise InvalidOperation("quantidade deve ser maior que zero")
        price = to_decimal(unit_price)
        amt = (price * qty).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        return qty, price, amt
    amt = to_decimal(amount)
    return Decimal("1"), amt, amt


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
        Retorna uma conexao com row_factory configurado e deteccao de tipo
        declarado ativada (necessaria para o converter de DECIMAL).
        Para :memory:, reutiliza a conexao persistente.
        Para arquivos, cria uma nova conexao (thread-safe).
        """
        if self._is_memory:
            if self._mem_conn is None:
                self._mem_conn = sqlite3.connect(
                    ":memory:", detect_types=sqlite3.PARSE_DECLTYPES
                )
                self._mem_conn.row_factory = sqlite3.Row
            return self._mem_conn
        else:
            conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
            conn.row_factory = sqlite3.Row
            return conn

    @contextmanager
    def _connection(self):
        """
        Fornece uma conexao pronta para uso (nova para arquivos, reaproveitada
        para :memory:), sempre encerrando corretamente ao sair do bloco `with`.

        Em caso de excecao, faz ROLLBACK antes de fechar/liberar a conexao.
        Isso e essencial sobretudo para :memory:, cuja conexao e persistente
        e reaproveitada entre chamadas: sem esse rollback, uma escrita nao
        commitada de uma chamada que falhou no meio ficaria "pendurada" na
        conexao e seria commitada silenciosamente pela PROXIMA chamada
        bem-sucedida que reusar essa mesma conexao (testado empiricamente:
        sem rollback explicito, um INSERT de uma operacao que lancou uma
        excecao no meio do processo acabava persistido junto com o commit()
        de uma operacao seguinte totalmente independente).

        Para conexoes de arquivo, fechar sem commit ja causa rollback
        implicito no SQLite, mas o rollback explicito aqui e mantido para
        nao depender desse comportamento implicito e para garantir o mesmo
        contrato em ambos os casos (arquivo e memoria).
        """
        conn = self._connect()
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        finally:
            if not self._is_memory:
                conn.close()

    @staticmethod
    def _table_columns(conn: sqlite3.Connection, table: str) -> Dict[str, str]:
        """
        Retorna {nome_da_coluna: tipo_declarado} de uma tabela via
        PRAGMA table_info. NOTA: `table` nunca vem de entrada do usuario
        (sempre um literal fixo no proprio codigo), entao a interpolacao
        direta no SQL abaixo e segura.
        """
        return {row["name"]: (row["type"] or "") for row in conn.execute(f"PRAGMA table_info({table})")}

    def _init_tables(self) -> None:
        """Create the expenses and balance tables if they do not already exist."""
        try:
            with self._connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS expenses (
                        id          INTEGER PRIMARY KEY AUTOINCREMENT,
                        category    TEXT    NOT NULL,
                        subcategory TEXT,
                        description TEXT    NOT NULL,
                        amount      DECIMAL NOT NULL,
                        quantity    DECIMAL NOT NULL DEFAULT 1,
                        unit_price  DECIMAL,
                        created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS balance (
                        id              INTEGER PRIMARY KEY CHECK (id = 1),
                        amount          DECIMAL NOT NULL DEFAULT 0,
                        salary          DECIMAL NOT NULL DEFAULT 0,
                        last_salary_month TEXT,
                        last_salary_date  TEXT
                    )
                    """
                )
                conn.commit()
        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to init tables: {e}")

    def _migrate_tables(self) -> None:
        """Adiciona colunas novas em tabelas existentes (migracao automatica)
        e converte colunas monetarias antigas (REAL/float) para DECIMAL."""
        try:
            with self._connection() as conn:
                columns = self._table_columns(conn, "balance")
                if "salary" not in columns:
                    conn.execute("ALTER TABLE balance ADD COLUMN salary DECIMAL NOT NULL DEFAULT 0")
                if "last_salary_month" not in columns:
                    conn.execute("ALTER TABLE balance ADD COLUMN last_salary_month TEXT")
                if "last_salary_date" not in columns:
                    conn.execute("ALTER TABLE balance ADD COLUMN last_salary_date TEXT")
                conn.commit()

                # Migra colunas antigas (REAL) para DECIMAL primeiro, pois esse
                # caminho recria a tabela expenses ja com o schema completo
                # (incluindo subcategory/quantity/unit_price).
                self._migrate_amount_columns_to_decimal(conn)

                # Bancos que ja estavam em DECIMAL (versao anterior deste app,
                # antes de subcategoria/quantidade existirem) ainda podem nao
                # ter essas colunas -- adiciona de forma aditiva se faltarem.
                expense_columns = self._table_columns(conn, "expenses")
                if "subcategory" not in expense_columns:
                    conn.execute("ALTER TABLE expenses ADD COLUMN subcategory TEXT")
                if "quantity" not in expense_columns:
                    conn.execute("ALTER TABLE expenses ADD COLUMN quantity DECIMAL NOT NULL DEFAULT 1")
                if "unit_price" not in expense_columns:
                    conn.execute("ALTER TABLE expenses ADD COLUMN unit_price DECIMAL")
                    # Para despesas ja existentes, o preco unitario "efetivo"
                    # e o proprio valor total (quantidade implicita = 1).
                    conn.execute("UPDATE expenses SET unit_price = amount WHERE unit_price IS NULL")
                conn.commit()
        except sqlite3.Error as e:
            print(f"[DB MIGRATE] {e}")

    def _migrate_amount_columns_to_decimal(self, conn: sqlite3.Connection) -> None:
        """
        Bancos criados por versoes anteriores do app tem `amount`/`salary`
        declarados como REAL (float). Aqui detectamos isso via
        PRAGMA table_info e recriamos as tabelas com colunas DECIMAL,
        convertendo cada valor existente com `to_decimal(valor)` para
        preservar o valor "visual" original (ex.: 19.99), em vez de herdar
        o ruido binario do float.
        """
        # --- expenses.amount ---
        cols = self._table_columns(conn, "expenses")
        if cols.get("amount", "").upper() != "DECIMAL":
            rows = conn.execute(
                "SELECT id, category, description, amount, created_at FROM expenses"
            ).fetchall()
            conn.execute("ALTER TABLE expenses RENAME TO expenses_legacy_float")
            conn.execute(
                """
                CREATE TABLE expenses (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    category    TEXT    NOT NULL,
                    subcategory TEXT,
                    description TEXT    NOT NULL,
                    amount      DECIMAL NOT NULL,
                    quantity    DECIMAL NOT NULL DEFAULT 1,
                    unit_price  DECIMAL,
                    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
                )
                """
            )
            for r in rows:
                legacy_amount = to_decimal(r["amount"] if r["amount"] is not None else 0)
                conn.execute(
                    "INSERT INTO expenses (id, category, subcategory, description, amount, quantity, unit_price, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        r["id"],
                        r["category"],
                        None,
                        r["description"],
                        legacy_amount,
                        Decimal("1"),
                        legacy_amount,
                        r["created_at"],
                    ),
                )
            conn.execute("DROP TABLE expenses_legacy_float")
            conn.commit()

        # --- balance.amount / balance.salary ---
        cols = self._table_columns(conn, "balance")
        needs_migration = (
            cols.get("amount", "").upper() != "DECIMAL"
            or cols.get("salary", "").upper() != "DECIMAL"
        )
        if needs_migration:
            row = conn.execute(
                "SELECT id, amount, salary, last_salary_month, last_salary_date "
                "FROM balance WHERE id = 1"
            ).fetchone()
            conn.execute("ALTER TABLE balance RENAME TO balance_legacy_float")
            conn.execute(
                """
                CREATE TABLE balance (
                    id                INTEGER PRIMARY KEY CHECK (id = 1),
                    amount            DECIMAL NOT NULL DEFAULT 0,
                    salary            DECIMAL NOT NULL DEFAULT 0,
                    last_salary_month TEXT,
                    last_salary_date  TEXT
                )
                """
            )
            if row:
                conn.execute(
                    "INSERT INTO balance (id, amount, salary, last_salary_month, last_salary_date) "
                    "VALUES (1, ?, ?, ?, ?)",
                    (
                        to_decimal(row["amount"] if row["amount"] is not None else 0),
                        to_decimal(row["salary"] if row["salary"] is not None else 0),
                        row["last_salary_month"],
                        row["last_salary_date"],
                    ),
                )
            conn.execute("DROP TABLE balance_legacy_float")
            conn.commit()

    # ------------------------------------------------------------------
    # Expenses CRUD
    # ------------------------------------------------------------------
    def _prepare_expense_fields(
        self,
        category: str,
        description: str,
        amount: Any,
        subcategory: Optional[str],
        quantity: Any,
        unit_price: Any,
    ):
        """
        Resolve os campos de uma despesa antes de gravar: calcula o valor
        final (direto, ou preco unitario x quantidade) e normaliza
        categoria/subcategoria/descricao. Compartilhado por add_expense e
        update_expense. Pode levantar InvalidOperation/ValueError/TypeError
        para entradas invalidas.
        """
        qty, price, amt = resolve_amount(amount, quantity, unit_price)
        sub = (subcategory or "").strip() or None
        return category.strip(), sub, description.strip(), amt, qty, price

    def add_expense(
        self,
        category: str,
        description: str,
        amount: Any = None,
        subcategory: Optional[str] = None,
        quantity: Any = None,
        unit_price: Any = None,
    ) -> Dict[str, Any]:
        try:
            cat, sub, desc, amt, qty, price = self._prepare_expense_fields(
                category, description, amount, subcategory, quantity, unit_price
            )
        except (InvalidOperation, ValueError, TypeError):
            return {"success": False, "id": None, "message": f"Valor invalido: '{amount}'"}
        try:
            with self._connection() as conn:
                cursor = conn.execute(
                    "INSERT INTO expenses (category, subcategory, description, amount, quantity, unit_price) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (cat, sub, desc, amt, qty, price),
                )
                conn.commit()
                last_id = cursor.lastrowid
            return {"success": True, "id": last_id, "amount": amt, "message": "Despesa registrada com sucesso!"}
        except sqlite3.Error as e:
            return {"success": False, "id": None, "message": f"Erro ao salvar: {e}"}

    def add_expenses_bulk(self, category: str, lines: str) -> Dict[str, Any]:
        inserted = 0
        errors = []
        total = Decimal("0")
        category = category.strip()
        try:
            with self._connection() as conn:
                for line in lines.strip().splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    parts = [p.strip() for p in line.split(",", 1)]
                    if len(parts) != 2:
                        errors.append(f"Formato invalido: '{line}'")
                        continue
                    desc, val_str = parts
                    try:
                        cleaned = val_str.replace("R$", "").replace("$", "").strip()
                        cleaned = cleaned.replace(",", ".")
                        amount = to_decimal(cleaned)
                    except (InvalidOperation, ValueError):
                        errors.append(f"Valor invalido: '{val_str}'")
                        continue
                    conn.execute(
                        "INSERT INTO expenses (category, description, amount) VALUES (?, ?, ?)",
                        (category, desc, amount),
                    )
                    inserted += 1
                    total += amount
                conn.commit()
            msg = f"{inserted} despesa(s) inserida(s)."
            if errors:
                msg += f" {len(errors)} erro(s) encontrado(s)."
            return {
                "success": True,
                "inserted": inserted,
                "errors": errors,
                "total": total,
                "message": msg,
            }
        except sqlite3.Error as e:
            return {
                "success": False,
                "inserted": inserted,
                "errors": errors,
                "total": total,
                "message": f"Erro em massa: {e}",
            }

    def add_expenses_structured(
        self, category: str, subcategory: Optional[str], products: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Insere varias despesas de uma vez, todas com a mesma categoria e
        subcategoria, uma por "produto" (nome + preco unitario + quantidade
        com stepper +/-). Usado pelo formulario unificado de Nova Despesa,
        que substituiu o antigo Cadastro em Massa (texto colado) por uma
        lista estruturada de produtos.

        `products`: lista de dicts com "description", "unit_price" e
        "quantity". Mantem o mesmo formato de retorno de add_expenses_bulk
        (inserted/errors/total) para reaproveitar a logica de desconto de
        saldo ja existente no app.py.
        """
        inserted = 0
        errors = []
        total = Decimal("0")
        cat = category.strip()
        sub = (subcategory or "").strip() or None
        try:
            with self._connection() as conn:
                for item in products:
                    desc = str(item.get("description", "")).strip()
                    try:
                        qty, price, amt = resolve_amount(None, item.get("quantity"), item.get("unit_price"))
                    except (InvalidOperation, ValueError, TypeError):
                        errors.append(f"Dados invalidos: {item}")
                        continue
                    if not desc or amt <= 0:
                        errors.append(f"Dados invalidos: {item}")
                        continue
                    conn.execute(
                        "INSERT INTO expenses (category, subcategory, description, amount, quantity, unit_price) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (cat, sub, desc, amt, qty, price),
                    )
                    inserted += 1
                    total += amt
                conn.commit()
            return {
                "success": True,
                "inserted": inserted,
                "errors": errors,
                "total": total,
                "message": f"{inserted} despesa(s) registrada(s).",
            }
        except sqlite3.Error as e:
            return {
                "success": False,
                "inserted": inserted,
                "errors": errors,
                "total": total,
                "message": str(e),
            }

    def get_expense(self, expense_id: int) -> Dict[str, Any]:
        try:
            with self._connection() as conn:
                row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
            if row:
                return {"success": True, "data": dict(row)}
            return {"success": False, "data": None, "message": "Despesa nao encontrada."}
        except sqlite3.Error as e:
            return {"success": False, "data": None, "message": str(e)}

    def update_expense(
        self,
        expense_id: int,
        category: str,
        description: str,
        amount: Any = None,
        subcategory: Optional[str] = None,
        quantity: Any = None,
        unit_price: Any = None,
        date_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        `date_str`, se informado (formato "YYYY-MM-DD"), atualiza a data da
        despesa preservando o horario original (created_at guarda
        "YYYY-MM-DD HH:MM:SS"; so o dia muda). Se None, a data nao e tocada.
        """
        try:
            cat, sub, desc, amt, qty, price = self._prepare_expense_fields(
                category, description, amount, subcategory, quantity, unit_price
            )
        except (InvalidOperation, ValueError, TypeError):
            return {"success": False, "message": f"Valor invalido: '{amount}'"}

        if date_str is not None:
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                return {"success": False, "message": "Data invalida."}

        try:
            with self._connection() as conn:
                if date_str is not None:
                    row = conn.execute("SELECT created_at FROM expenses WHERE id = ?", (expense_id,)).fetchone()
                    if not row:
                        return {"success": False, "message": "Despesa nao encontrada para atualizar."}
                    old_created_at = row["created_at"] or ""
                    time_part = old_created_at.split(" ", 1)[1] if " " in old_created_at else "00:00:00"
                    new_created_at = f"{date_str} {time_part}"
                    cursor = conn.execute(
                        "UPDATE expenses SET category = ?, subcategory = ?, description = ?, amount = ?, "
                        "quantity = ?, unit_price = ?, created_at = ? WHERE id = ?",
                        (cat, sub, desc, amt, qty, price, new_created_at, expense_id),
                    )
                else:
                    cursor = conn.execute(
                        "UPDATE expenses SET category = ?, subcategory = ?, description = ?, amount = ?, "
                        "quantity = ?, unit_price = ? WHERE id = ?",
                        (cat, sub, desc, amt, qty, price, expense_id),
                    )
                conn.commit()
                rowcount = cursor.rowcount
            if rowcount == 0:
                return {"success": False, "message": "Despesa nao encontrada para atualizar."}
            return {"success": True, "amount": amt, "message": "Despesa atualizada com sucesso!"}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Erro ao atualizar: {e}"}

    def delete_expense(self, expense_id: int) -> Dict[str, Any]:
        try:
            with self._connection() as conn:
                cursor = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
                conn.commit()
                rowcount = cursor.rowcount
            if rowcount == 0:
                return {"success": False, "message": "Despesa nao encontrada para excluir."}
            return {"success": True, "message": "Despesa excluida com sucesso!"}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Erro ao excluir: {e}"}

    # ------------------------------------------------------------------
    # Balance / Account
    # ------------------------------------------------------------------
    def _fetch_balance_row(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """
        Le a linha (unica) da tabela balance, com defaults caso ainda nao
        exista nenhuma. Centraliza esse fetch para get_balance, get_salary,
        set_balance, set_salary, add_salary_to_balance e
        subtract_from_balance, que precisam ler-e-regravar todos os campos
        para nao apagar acidentalmente salario/datas ao atualizar so um
        deles (bug ja corrigido antes; manter isso em um unico lugar evita
        que ele volte caso um metodo futuro esqueca de preservar algum
        campo).
        """
        row = conn.execute(
            "SELECT amount, salary, last_salary_month, last_salary_date FROM balance WHERE id = 1"
        ).fetchone()
        if row:
            return dict(row)
        return {
            "amount": Decimal("0"),
            "salary": Decimal("0"),
            "last_salary_month": None,
            "last_salary_date": None,
        }

    def _save_balance_row(
        self,
        conn: sqlite3.Connection,
        amount: Decimal,
        salary: Decimal,
        last_salary_month: Optional[str],
        last_salary_date: Optional[str],
    ) -> None:
        """Grava a linha unica da tabela balance, sempre com os 5 campos."""
        conn.execute(
            "INSERT OR REPLACE INTO balance (id, amount, salary, last_salary_month, last_salary_date) "
            "VALUES (1, ?, ?, ?, ?)",
            (amount, salary, last_salary_month, last_salary_date),
        )

    def get_balance(self) -> Dict[str, Any]:
        """Return current account balance."""
        try:
            with self._connection() as conn:
                current = self._fetch_balance_row(conn)
            return {"success": True, "balance": current["amount"], "last_salary_date": current["last_salary_date"]}
        except sqlite3.Error as e:
            return {"success": False, "balance": Decimal("0"), "message": str(e)}

    def set_balance(self, amount: Any) -> Dict[str, Any]:
        """Set account balance (overwrite), preserving salary."""
        try:
            amt = to_decimal(amount)
        except (InvalidOperation, ValueError, TypeError):
            return {"success": False, "message": f"Valor invalido: '{amount}'"}
        try:
            with self._connection() as conn:
                current = self._fetch_balance_row(conn)
                self._save_balance_row(
                    conn, amt, current["salary"], current["last_salary_month"], current["last_salary_date"]
                )
                conn.commit()
            return {"success": True, "balance": amt, "message": "Saldo atualizado."}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Erro ao atualizar saldo: {e}"}

    def get_salary(self) -> Dict[str, Any]:
        """Return configured monthly salary."""
        try:
            with self._connection() as conn:
                current = self._fetch_balance_row(conn)
            return {
                "success": True,
                "salary": current["salary"],
                "last_salary_month": current["last_salary_month"],
                "last_salary_date": current["last_salary_date"],
            }
        except sqlite3.Error as e:
            return {"success": False, "salary": Decimal("0"), "message": str(e)}

    def set_salary(self, amount: Any) -> Dict[str, Any]:
        """Set monthly salary amount."""
        try:
            amt = to_decimal(amount)
        except (InvalidOperation, ValueError, TypeError):
            return {"success": False, "message": f"Valor invalido: '{amount}'"}
        try:
            with self._connection() as conn:
                current = self._fetch_balance_row(conn)
                self._save_balance_row(
                    conn, current["amount"], amt, current["last_salary_month"], current["last_salary_date"]
                )
                conn.commit()
            return {"success": True, "salary": amt, "message": "Salario configurado."}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Erro ao configurar salario: {e}"}

    def add_salary_to_balance(self) -> Dict[str, Any]:
        """Add monthly salary to current balance."""
        try:
            with self._connection() as conn:
                current = self._fetch_balance_row(conn)
                if current["salary"] <= 0:
                    return {"success": False, "message": "Salario nao configurado."}
                new_balance = current["amount"] + current["salary"]
                today_str = datetime.now().strftime("%Y-%m-%d")
                self._save_balance_row(
                    conn, new_balance, current["salary"], current["last_salary_month"], today_str
                )
                conn.commit()
            return {
                "success": True,
                "balance": new_balance,
                "salary": current["salary"],
                "message": f"Salario de R$ {current['salary']:.2f} creditado.",
            }
        except sqlite3.Error as e:
            return {"success": False, "message": f"Erro ao creditar salario: {e}"}

    def check_auto_salary(self) -> Dict[str, Any]:
        """Verifica se passaram 30 dias desde o ultimo credito de salario."""
        try:
            res = self.get_salary()
            if res["salary"] <= 0:
                return {"success": True, "should_credit": False, "days_remaining": 0, "message": "Salario nao configurado."}

            last_date_str = res.get("last_salary_date")
            if not last_date_str:
                # Nunca creditado — credita na primeira vez que abrir o app
                credit_res = self.add_salary_to_balance()
                return {"success": True, "should_credit": True, "days_remaining": 0, "message": credit_res["message"]}

            last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
            today = datetime.now()
            days_passed = (today - last_date).days

            if days_passed >= 30:
                credit_res = self.add_salary_to_balance()
                return {"success": True, "should_credit": True, "days_remaining": 0, "days_passed": days_passed, "message": credit_res["message"]}

            return {"success": True, "should_credit": False, "days_remaining": 30 - days_passed, "days_passed": days_passed}
        except Exception as e:
            return {"success": False, "should_credit": False, "message": str(e)}

    def set_last_salary_month(self, month: str) -> Dict[str, Any]:
        """Mark that salary was already credited for this month."""
        try:
            with self._connection() as conn:
                conn.execute("UPDATE balance SET last_salary_month = ? WHERE id = 1", (month,))
                conn.commit()
            return {"success": True}
        except sqlite3.Error as e:
            return {"success": False, "message": str(e)}

    def subtract_from_balance(self, amount: Any) -> Dict[str, Any]:
        """Subtract expense amount from balance (preserva salario e demais campos)."""
        try:
            amt = to_decimal(amount)
        except (InvalidOperation, ValueError, TypeError):
            return {"success": False, "message": f"Valor invalido: '{amount}'"}
        try:
            with self._connection() as conn:
                current = self._fetch_balance_row(conn)
                new_balance = current["amount"] - amt
                self._save_balance_row(
                    conn, new_balance, current["salary"], current["last_salary_month"], current["last_salary_date"]
                )
                conn.commit()
            return {"success": True, "balance": new_balance, "message": f"Saldo: {new_balance:.2f}"}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Erro ao subtrair saldo: {e}"}

    def set_next_salary_date(self, date_str: str) -> Dict[str, Any]:
        """
        Define a PROXIMA data em que o salario deve ser recebido.

        E guardada internamente como last_salary_date = data_informada -
        30 dias, para que tanto o auto-credito (que dispara 30 dias apos
        last_salary_date, em check_auto_salary) quanto o calendario de
        salarios (get_salary_calendar, que projeta a partir dela) fiquem
        consistentes com a mesma data-ancora.
        """
        try:
            next_date = datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            return {"success": False, "message": "Data invalida."}
        anchor = (next_date - timedelta(days=30)).strftime("%Y-%m-%d")
        try:
            with self._connection() as conn:
                current = self._fetch_balance_row(conn)
                self._save_balance_row(
                    conn, current["amount"], current["salary"], current["last_salary_month"], anchor
                )
                conn.commit()
            return {"success": True, "next_salary_date": date_str, "message": "Data de recebimento atualizada."}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Erro ao atualizar data: {e}"}

    def get_salary_calendar(self, vacation_month: int, count: int = 12) -> Dict[str, Any]:
        """
        Retorna as proximas `count` datas de recebimento de salario, cada
        uma exatamente 30 dias apos a anterior, a partir de
        last_salary_date. Corrige o bug de assumir "o mesmo dia do mes
        para todos": como os meses tem tamanhos diferentes, 30 dias apos
        um recebimento em 15/02 cai em 17/03, nao em 15/03 -- entao a
        "data do mes" tem que derivar do ciclo real, nao ficar fixa.

        A ocorrencia cujo mes bate com `vacation_month` (1-12) vem com
        is_vacation=True e o valor liquido de ferias, em vez do salario
        bruto. Se ainda nao houver last_salary_date configurada, retorna
        lista vazia com has_reference_date=False (o frontend pede para o
        usuario configurar a data antes de mostrar o calendario).
        """
        try:
            with self._connection() as conn:
                current = self._fetch_balance_row(conn)
            salary = current["salary"]
            anchor_str = current["last_salary_date"]

            if not anchor_str:
                return {"success": True, "data": [], "has_reference_date": False}

            anchor = datetime.strptime(anchor_str, "%Y-%m-%d")
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            # O proprio anchor (last_salary_date) representa o ULTIMO
            # credito, nunca um pagamento futuro valido -- o primeiro
            # candidato e sempre anchor+30. Sem isso, se a "proxima data de
            # recebimento" configurada estiver a mais de 30 dias de hoje,
            # o anchor (= proxima_data - 30) ja cairia >= hoje e seria
            # exibido diretamente, um ciclo inteiro ANTES da data que a
            # pessoa realmente informou.
            next_date = anchor + timedelta(days=30)
            while next_date < today:
                next_date += timedelta(days=30)

            entries = []
            for i in range(count):
                d = next_date + timedelta(days=30 * i)
                is_vacation = d.month == vacation_month
                entry: Dict[str, Any] = {"date": d.strftime("%Y-%m-%d"), "is_vacation": is_vacation}
                if salary <= 0:
                    entry["amount"] = None
                    entry["label"] = "Nao configurado"
                elif is_vacation:
                    ferias = Database.calcular_ferias(salary)
                    entry["amount"] = ferias["salario_liquido"] if ferias.get("success") else None
                    entry["label"] = "Ferias (liquido)"
                else:
                    entry["amount"] = salary
                    entry["label"] = "Salario mensal"
                entries.append(entry)

            return {"success": True, "data": entries, "has_reference_date": True}
        except sqlite3.Error as e:
            return {"success": False, "data": [], "message": str(e)}

    # ------------------------------------------------------------------
    # Aggregation / drill-down
    # ------------------------------------------------------------------
    @staticmethod
    def _grouped_totals(
        rows: List[sqlite3.Row],
        key_field: str,
        output_field: str,
        sort_by_total: bool = True,
        normalize_key: Optional[Callable[[Any], Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Agrupa `rows` (que tem `key_field` e `amount`) somando os valores
        em Decimal e contando ocorrencias por chave. Usado por
        get_months_summary, get_categories_by_month e
        get_subcategories_by_month_and_category, que faziam essa mesma
        agregacao de forma quase identica.

        `normalize_key` transforma a chave antes de agrupar (ex.: None ->
        "", usado para o balde "sem subcategoria"). `sort_by_total` ordena
        pelo total (decrescente, usado por categoria/subcategoria); quando
        False, ordena pela propria chave decrescente (usado por mes, no
        formato "YYYY-MM").
        """
        totals: Dict[Any, Decimal] = {}
        counts: Dict[Any, int] = {}
        for r in rows:
            key = r[key_field]
            if normalize_key is not None:
                key = normalize_key(key)
            totals[key] = totals.get(key, Decimal("0")) + r["amount"]
            counts[key] = counts.get(key, 0) + 1

        if sort_by_total:
            ordered_keys = sorted(totals, key=lambda k: totals[k], reverse=True)
        else:
            ordered_keys = sorted(totals, reverse=True)

        return [{output_field: k, "total": totals[k], "count": counts[k]} for k in ordered_keys]

    def get_months_summary(self) -> Dict[str, Any]:
        try:
            with self._connection() as conn:
                rows = conn.execute(
                    "SELECT strftime('%Y-%m', created_at) AS month, amount FROM expenses"
                ).fetchall()
            data = self._grouped_totals(rows, "month", "month", sort_by_total=False)
            return {"success": True, "data": data}
        except sqlite3.Error as e:
            return {"success": False, "data": [], "message": str(e)}

    def get_categories_by_month(self, month: str) -> Dict[str, Any]:
        try:
            with self._connection() as conn:
                rows = conn.execute(
                    "SELECT category, amount FROM expenses WHERE strftime('%Y-%m', created_at) = ?",
                    (month,),
                ).fetchall()
            data = self._grouped_totals(rows, "category", "category")
            return {"success": True, "data": data}
        except sqlite3.Error as e:
            return {"success": False, "data": [], "message": str(e)}

    def get_subcategories_by_month_and_category(self, month: str, category: str) -> Dict[str, Any]:
        """
        Agrupa as despesas de uma categoria/mes por subcategoria. Despesas
        sem subcategoria (None ou string vazia) caem no balde de chave "",
        exibido no frontend como "Sem subcategoria".
        """
        try:
            with self._connection() as conn:
                rows = conn.execute(
                    "SELECT subcategory, amount FROM expenses "
                    "WHERE strftime('%Y-%m', created_at) = ? AND category = ?",
                    (month, category),
                ).fetchall()
            data = self._grouped_totals(rows, "subcategory", "subcategory", normalize_key=lambda v: v or "")
            return {"success": True, "data": data}
        except sqlite3.Error as e:
            return {"success": False, "data": [], "message": str(e)}

    def get_expenses_by_month_and_category(self, month: str, category: str, subcategory: Optional[str] = None) -> Dict[str, Any]:
        """
        `subcategory`:
          - None  -> nao filtra (retorna todas as despesas da categoria)
          - ""    -> filtra apenas despesas SEM subcategoria
          - "X"   -> filtra despesas cuja subcategoria seja exatamente "X"
        """
        try:
            sql = (
                "SELECT id, category, subcategory, description, amount, quantity, unit_price, created_at "
                "FROM expenses WHERE strftime('%Y-%m', created_at) = ? AND category = ?"
            )
            params: List[Any] = [month, category]
            if subcategory == "":
                sql += " AND (subcategory IS NULL OR subcategory = '')"
            elif subcategory is not None:
                sql += " AND subcategory = ?"
                params.append(subcategory)
            sql += " ORDER BY created_at DESC"
            with self._connection() as conn:
                rows = conn.execute(sql, params).fetchall()
            return {"success": True, "data": [dict(r) for r in rows]}
        except sqlite3.Error as e:
            return {"success": False, "data": [], "message": str(e)}

    def get_all_categories(self) -> Dict[str, Any]:
        try:
            with self._connection() as conn:
                rows = conn.execute("SELECT DISTINCT category FROM expenses ORDER BY category").fetchall()
            return {"success": True, "data": [r["category"] for r in rows]}
        except sqlite3.Error as e:
            return {"success": False, "data": [], "message": str(e)}

    def get_all_subcategories(self) -> Dict[str, Any]:
        """Lista de subcategorias distintas ja usadas (para autocomplete)."""
        try:
            with self._connection() as conn:
                rows = conn.execute(
                    "SELECT DISTINCT subcategory FROM expenses "
                    "WHERE subcategory IS NOT NULL AND subcategory != '' "
                    "ORDER BY subcategory"
                ).fetchall()
            return {"success": True, "data": [r["subcategory"] for r in rows]}
        except sqlite3.Error as e:
            return {"success": False, "data": [], "message": str(e)}

    # ------------------------------------------------------------------
    # Ferias (logica extraida de calcular_ferias.py)
    # ------------------------------------------------------------------
    @staticmethod
    def calcular_ferias(salario_bruto: Any) -> Dict[str, Any]:
        try:
            # Valores de entrada/saida em centavos exatos; os calculos
            # intermediarios (bases, faixas) mantem precisao total e so
            # sao arredondados para 2 casas na hora de montar o retorno,
            # exatamente como a versao original fazia com round(x, 2).
            sb = to_decimal(salario_bruto)
            constitucional = sb / Decimal("3")
            total_bruto = sb + constitucional

            # INSS progressivo
            faixas_inss = [
                (Decimal("1621.00"), Decimal("0.075")),
                (Decimal("2902.84"), Decimal("0.09")),
                (Decimal("4354.27"), Decimal("0.12")),
                (Decimal("8475.55"), Decimal("0.14")),
            ]
            anterior = Decimal("0")
            inss_val = Decimal("0")
            for limite, aliquota in faixas_inss:
                if total_bruto >= limite:
                    inss_val += (limite - anterior) * aliquota
                    anterior = limite
                else:
                    inss_val += (total_bruto - anterior) * aliquota
                    break

            base_irrf = total_bruto - inss_val

            # IRRF
            faixas_irrf = [
                (Decimal("2428.80"), Decimal("0"), Decimal("0.00")),
                (Decimal("2826.65"), Decimal("0.075"), Decimal("182.16")),
                (Decimal("3751.05"), Decimal("0.15"), Decimal("394.16")),
                (Decimal("4664.68"), Decimal("0.225"), Decimal("675.49")),
            ]
            irrf_val = Decimal("0")
            for limite, aliquota, parcela in faixas_irrf:
                if base_irrf <= limite:
                    irrf_val = (base_irrf * aliquota) - parcela
                    break
            else:
                irrf_val = (base_irrf * Decimal("0.275")) - Decimal("908.73")

            # Desconto adicional (nova regra)
            if base_irrf <= Decimal("5000.00"):
                desconto_adicional = base_irrf
            elif base_irrf <= Decimal("7350.00"):
                desconto_adicional = Decimal("978.62") - (Decimal("0.133145") * base_irrf)
            else:
                desconto_adicional = Decimal("0")

            irrf_final = max(Decimal("0"), irrf_val - desconto_adicional)
            salario_liquido = base_irrf - irrf_final

            def q(d: Decimal) -> Decimal:
                return d.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

            return {
                "success": True,
                "salario_bruto": q(sb),
                "terco_constitucional": q(constitucional),
                "total_bruto": q(total_bruto),
                "inss": q(inss_val),
                "base_irrf": q(base_irrf),
                "irrf_calculado": q(irrf_val),
                "desconto_adicional": q(desconto_adicional),
                "irrf_final": q(irrf_final),
                "salario_liquido": q(salario_liquido),
            }
        except (InvalidOperation, ValueError, TypeError) as e:
            return {"success": False, "message": str(e)}

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
                amount = to_decimal(val_str)
            except (InvalidOperation, ValueError):
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
        total = Decimal("0")
        category = category.strip()
        try:
            with self._connection() as conn:
                for item in parsed_list:
                    desc = str(item.get("description", "")).strip()
                    try:
                        amount = to_decimal(item.get("amount", 0))
                    except (InvalidOperation, ValueError, TypeError):
                        errors.append(f"Dados invalidos: {item}")
                        continue
                    if not desc or amount <= 0:
                        errors.append(f"Dados invalidos: {item}")
                        continue
                    conn.execute(
                        "INSERT INTO expenses (category, description, amount) VALUES (?, ?, ?)",
                        (category, desc, amount),
                    )
                    inserted += 1
                    total += amount
                conn.commit()
            return {
                "success": True,
                "inserted": inserted,
                "errors": errors,
                "total": total,
                "message": f"{inserted} despesa(s) salva(s).",
            }
        except sqlite3.Error as e:
            return {
                "success": False,
                "inserted": inserted,
                "errors": errors,
                "total": total,
                "message": str(e),
            }
