#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
database.py - Camada de Persistencia / Repositorio para o Controlador de
Gastos.

Limitado estritamente a: abrir conexoes, criar/migrar tabelas e executar
comandos SQL diretos (SELECT, INSERT, UPDATE, DELETE). Este modulo NAO
contém fórmulas de impostos, condições sobre datas de salário, nem
decisões de negócio -- por exemplo, ele não decide "como calcular o valor
de uma despesa" (preco unitario x quantidade) nem "quando o saldo deve
ser ajustado". Essas responsabilidades ficam nos modulos em services/:

    - services/payroll.py   -> calculo de ferias, tabelas de INSS/IRRF
    - services/finance.py   -> saldo, ajuste de saldo em despesas, parser
    - services/scheduler.py -> ciclo de 30 dias e credito automatico de salario

NOTA: Para bancos ':memory:', mantem uma conexão persistente aberta,
pois o SQLite destroi o banco em memoria quando a ultima conexão e fechada.

VALORES MONETARIOS
-------------------
Todo valor em dinheiro e representado internamente com `decimal.Decimal`
(nunca `float`), e persistido em colunas SQLite declaradas como `DECIMAL`.

O SQLite não possui um tipo decimal nativo: colunas `NUMERIC`/`DECIMAL`
convertem automaticamente texto "bem formado" (ex.: "19.99") para o
storage class REAL (float de 64 bits) por causa da chamada "type affinity"
de colunas numéricas. Para evitar isso, os valores Decimal são adaptados
para `bytes` (UTF-8) antes de irem para o SQLite: um valor BLOB não sofre
essa conversao automatica, entao o texto exato do Decimal e gravado sem
qualquer arredondamento binario. Um "converter" registrado faz o caminho
inverso ao ler, reconstruindo o Decimal a partir dos bytes.

Todas as agregações (somas por mês/categoria) são feitas em Python com
Decimal, e não via SQL SUM(), pois o SUM() do SQLite opera em ponto
flutuante internamente e reintroduziria os mesmos erros de arredondamento
que a adoção de Decimal busca eliminar. Isso continua sendo considerado
"consulta direta" (um relatório/agregação de leitura), não uma regra de
negocio, entao permanece aqui.
"""

import sqlite3
import os
from contextlib import contextmanager
from decimal import Decimal
from typing import List, Dict, Any, Optional, Callable

from services.decimal_utils import to_decimal


# ==============================================================================
# Decimal <-> SQLite bridging
# ==============================================================================
def _adapt_decimal(d: Decimal) -> bytes:
    """Adapta um Decimal para bytes (forca storage class BLOB no SQLite,
    imune a conversao automatica para REAL das colunas NUMERIC/DECIMAL)."""
    return format(d, "f").encode("utf-8")


def _convert_decimal(raw: bytes) -> Decimal:
    """Reconstroi um Decimal a partir dos bytes gravados no SQLite."""
    return Decimal(raw.decode("utf-8"))


sqlite3.register_adapter(Decimal, _adapt_decimal)
sqlite3.register_converter("DECIMAL", _convert_decimal)


class Database:
    """
    Repositório SQLite. Para arquivos, usa conexões novas a cada operação
    (thread-safe). Para :memory:, mantem uma conexão persistente.
    Todos os metodos retornam dicts com 'success' para tratamento no
    frontend (JS), mas nenhum deles decide "o que fazer" -- apenas
    executam a operação SQL pedida e relatam se deu certo.
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
        Retorna uma conexão com row_factory configurado e detecção de tipo
        declarado ativada (necessaria para o converter de DECIMAL).
        Para :memory:, reutiliza a conexão persistente.
        Para arquivos, cria uma nova conexão (thread-safe).
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
        Fornece uma conexão pronta para uso (nova para arquivos, reaproveitada
        para :memory:), sempre encerrando corretamente ao sair do bloco `with`.

        Em caso de exceção, faz ROLLBACK antes de fechar/liberar a conexão.
        Isso e essencial sobretudo para :memory:, cuja conexão e persistente
        é reaproveitada entre chamadas: sem esse rollback, uma escrita não
        commitada de uma chamada que falhou no meio ficaria "pendurada" na
        conexão e seria commitada silenciosamente pela PROXIMA chamada
        bem-sucedida que reusar essa mesma conexão.

        Para conexões de arquivo, fechar sem commit já causa rollback
        implícito no SQLite, mas o rollback explícito aqui é mantido para
        não depender desse comportamento implícito e para garantir o mesmo
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
        (sempre um literal fixo no próprio código), então a interpolação
        direta no SQL abaixo e segura.
        """
        return {row["name"]: (row["type"] or "") for row in conn.execute(f"PRAGMA table_info({table})")}

    # ------------------------------------------------------------------
    # Schema / migrações
    # ------------------------------------------------------------------
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
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS monthly_groups (
                        id                INTEGER PRIMARY KEY AUTOINCREMENT,
                        name              TEXT    NOT NULL,
                        last_applied_month TEXT
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS monthly_items (
                        id          INTEGER PRIMARY KEY AUTOINCREMENT,
                        group_id    INTEGER NOT NULL,
                        category    TEXT    NOT NULL,
                        subcategory TEXT,
                        description TEXT    NOT NULL,
                        quantity    DECIMAL NOT NULL DEFAULT 1,
                        unit_price  DECIMAL NOT NULL,
                        FOREIGN KEY (group_id) REFERENCES monthly_groups(id) ON DELETE CASCADE
                    )
                    """
                )
                conn.commit()
        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to init tables: {e}")

    def _migrate_tables(self) -> None:
        """Adiciona colunas novas em tabelas existentes (migração automática)
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
                # caminho recria a tabela expenses já com o schema completo
                # (incluindo subcategory/quantity/unit_price).
                self._migrate_amount_columns_to_decimal(conn)

                # Bancos que já estavam em DECIMAL (versão anterior deste app,
                # antes de subcategoria/quantidade existirem) ainda podem não
                # ter essas colunas -- adiciona de forma aditiva se faltarem.
                expense_columns = self._table_columns(conn, "expenses")
                if "subcategory" not in expense_columns:
                    conn.execute("ALTER TABLE expenses ADD COLUMN subcategory TEXT")
                if "quantity" not in expense_columns:
                    conn.execute("ALTER TABLE expenses ADD COLUMN quantity DECIMAL NOT NULL DEFAULT 1")
                if "unit_price" not in expense_columns:
                    conn.execute("ALTER TABLE expenses ADD COLUMN unit_price DECIMAL")
                    # Para despesas já existentes, o preço unitário "efetivo"
                    # e o proprio valor total (quantidade implicita = 1).
                    conn.execute("UPDATE expenses SET unit_price = amount WHERE unit_price IS NULL")
                conn.commit()

                # Grupos mensais: adiciona tabela e colunas faltantes para bancos
                # antigos que ainda não tinham a funcionalidade de despesas mensais.
                existing_tables = {
                    row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                }
                if "monthly_groups" not in existing_tables:
                    conn.execute(
                        """
                        CREATE TABLE monthly_groups (
                            id                INTEGER PRIMARY KEY AUTOINCREMENT,
                            name              TEXT    NOT NULL,
                            last_applied_month TEXT
                        )
                        """
                    )
                if "monthly_items" not in existing_tables:
                    conn.execute(
                        """
                        CREATE TABLE monthly_items (
                            id          INTEGER PRIMARY KEY AUTOINCREMENT,
                            group_id    INTEGER NOT NULL,
                            category    TEXT    NOT NULL,
                            subcategory TEXT,
                            description TEXT    NOT NULL,
                            quantity    DECIMAL NOT NULL DEFAULT 1,
                            unit_price  DECIMAL NOT NULL,
                            FOREIGN KEY (group_id) REFERENCES monthly_groups(id) ON DELETE CASCADE
                        )
                        """
                    )
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
        o ruído binário do float. Isso é migração de schema/dados, não
        regra de negocio -- por isso continua aqui.
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
    # Expenses: CRUD bruto (recebe valores já prontos; não calcula nada)
    # ------------------------------------------------------------------
    def insert_expense(
        self,
        category: str,
        subcategory: Optional[str],
        description: str,
        amount: Decimal,
        quantity: Decimal,
        unit_price: Decimal,
    ) -> Dict[str, Any]:
        """INSERT bruto de uma despesa. Os valores devem chegar já prontos
        (Decimal, categoria/descrição já normalizadas) -- quem decide como
        calcular `amount` a partir de preco x quantidade e o FinanceService."""
        try:
            with self._connection() as conn:
                cursor = conn.execute(
                    "INSERT INTO expenses (category, subcategory, description, amount, quantity, unit_price) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (category, subcategory, description, amount, quantity, unit_price),
                )
                conn.commit()
                last_id = cursor.lastrowid
            return {"success": True, "id": last_id, "message": "Despesa registrada com sucesso!", "key": "expense.add.success"}
        except sqlite3.Error as e:
            return {"success": False, "id": None, "message": f"Erro ao salvar: {e}", "key": "expense.add.error", "params": {"error": str(e)}}

    def insert_expenses_batch(self, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        INSERT de várias despesas na MESMA transação (atômico: tudo ou
        nada). Cada item de `rows` e um dict com category/subcategory/
        description/amount/quantity/unit_price já prontos.
        """
        if not rows:
            return {"success": True, "ids": []}
        try:
            ids = []
            with self._connection() as conn:
                for r in rows:
                    cursor = conn.execute(
                        "INSERT INTO expenses (category, subcategory, description, amount, quantity, unit_price) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (r["category"], r.get("subcategory"), r["description"], r["amount"], r["quantity"], r["unit_price"]),
                    )
                    ids.append(cursor.lastrowid)
                conn.commit()
            return {"success": True, "ids": ids}
        except sqlite3.Error as e:
            return {"success": False, "ids": [], "message": str(e)}

    def get_expense(self, expense_id: int) -> Dict[str, Any]:
        try:
            with self._connection() as conn:
                row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
            if row:
                return {"success": True, "data": dict(row)}
            return {"success": False, "data": None, "message": "Despesa não encontrada."}
        except sqlite3.Error as e:
            return {"success": False, "data": None, "message": str(e)}

    def update_expense_row(
        self,
        expense_id: int,
        category: str,
        subcategory: Optional[str],
        description: str,
        amount: Decimal,
        quantity: Decimal,
        unit_price: Decimal,
        created_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        UPDATE bruto de uma despesa. `created_at`, se informado (formato
        "YYYY-MM-DD HH:MM:SS" completo, já resolvido por quem chamou), e
        gravado também; se None, a data existente não é tocada.
        """
        try:
            with self._connection() as conn:
                if created_at is not None:
                    cursor = conn.execute(
                        "UPDATE expenses SET category = ?, subcategory = ?, description = ?, amount = ?, "
                        "quantity = ?, unit_price = ?, created_at = ? WHERE id = ?",
                        (category, subcategory, description, amount, quantity, unit_price, created_at, expense_id),
                    )
                else:
                    cursor = conn.execute(
                        "UPDATE expenses SET category = ?, subcategory = ?, description = ?, amount = ?, "
                        "quantity = ?, unit_price = ? WHERE id = ?",
                        (category, subcategory, description, amount, quantity, unit_price, expense_id),
                    )
                conn.commit()
                rowcount = cursor.rowcount
            if rowcount == 0:
                return {"success": False, "message": "Despesa não encontrada para atualizar.", "key": "expense.not_found"}
            return {"success": True, "message": "Despesa atualizada com sucesso!", "key": "expense.update.success"}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Erro ao atualizar: {e}", "key": "expense.update.error", "params": {"error": str(e)}}

    def delete_expense_row(self, expense_id: int) -> Dict[str, Any]:
        """DELETE bruto de uma despesa."""
        try:
            with self._connection() as conn:
                cursor = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
                conn.commit()
                rowcount = cursor.rowcount
            if rowcount == 0:
                return {"success": False, "message": "Despesa não encontrada para excluir.", "key": "expense.not_found"}
            return {"success": True, "message": "Despesa excluída com sucesso!", "key": "expense.delete.success"}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Erro ao excluir: {e}", "key": "expense.delete.error", "params": {"error": str(e)}}

    # ------------------------------------------------------------------
    # Expenses: consultas / relatorios (SELECT direto, sem regra de negocio)
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
        agregação de forma quase idêntica.
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
          - None  -> não filtra (retorna todas as despesas da categoria)
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
        """Lista de subcategorias distintas já usadas (para autocomplete)."""
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
    # Despesas Mensais: CRUD de grupos e itens (templates recorrentes)
    # ------------------------------------------------------------------
    def insert_monthly_group(self, name: str, items: List[Dict[str, Any]]) -> int:
        """
        Insere um grupo e seus itens na MESMA transação (atômico). Cada
        item de `items` já chega pronto: category/subcategory/description/
        quantity/unit_price/amount. Retorna o id do grupo criado.
        """
        with self._connection() as conn:
            cursor = conn.execute("INSERT INTO monthly_groups (name) VALUES (?)", (name,))
            group_id = cursor.lastrowid
            for it in items:
                conn.execute(
                    "INSERT INTO monthly_items (group_id, category, subcategory, description, quantity, unit_price) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (group_id, it["category"], it.get("subcategory"), it["description"],
                     it["quantity"], it["unit_price"]),
                )
            conn.commit()
            return group_id

    def update_monthly_group(self, group_id: int, name: str, items: List[Dict[str, Any]]) -> None:
        """Atualiza nome e SUBSTITUI todos os itens do grupo (na mesma
        transação). Não toca em last_applied_month."""
        with self._connection() as conn:
            conn.execute("UPDATE monthly_groups SET name = ? WHERE id = ?", (name, group_id))
            conn.execute("DELETE FROM monthly_items WHERE group_id = ?", (group_id,))
            for it in items:
                conn.execute(
                    "INSERT INTO monthly_items (group_id, category, subcategory, description, quantity, unit_price) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (group_id, it["category"], it.get("subcategory"), it["description"],
                     it["quantity"], it["unit_price"]),
                )
            conn.commit()

    def delete_monthly_group(self, group_id: int) -> None:
        """Exclui um grupo e seus itens (a tabela `expenses` não é tocada:
        despesas já lançadas pelo grupo permanecem no histórico)."""
        with self._connection() as conn:
            conn.execute("DELETE FROM monthly_items WHERE group_id = ?", (group_id,))
            conn.execute("DELETE FROM monthly_groups WHERE id = ?", (group_id,))
            conn.commit()

    def get_monthly_groups(self) -> List[Dict[str, Any]]:
        """Retorna todos os grupos com seus itens (quantity/unit_price
        já convertidos para Decimal pelo detect_types)."""
        with self._connection() as conn:
            group_rows = conn.execute(
                "SELECT id, name, last_applied_month FROM monthly_groups ORDER BY name"
            ).fetchall()
            item_rows = conn.execute(
                "SELECT id, group_id, category, subcategory, description, quantity, unit_price "
                "FROM monthly_items ORDER BY id"
            ).fetchall()

        items_by_group: Dict[int, List[Dict[str, Any]]] = {}
        for r in item_rows:
            items_by_group.setdefault(r["group_id"], []).append(dict(r))

        return [
            {
                "id": g["id"],
                "name": g["name"],
                "last_applied_month": g["last_applied_month"],
                "items": items_by_group.get(g["id"], []),
            }
            for g in group_rows
        ]

    def set_monthly_group_applied(self, group_id: int, month_key: str) -> None:
        """Marca o grupo como aplicado no mês informado ("YYYY-MM")."""
        with self._connection() as conn:
            conn.execute(
                "UPDATE monthly_groups SET last_applied_month = ? WHERE id = ?",
                (month_key, group_id),
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Balance: acesso bruto a linha unica da tabela `balance`
    # ------------------------------------------------------------------
    def fetch_balance_row(self) -> Dict[str, Any]:
        """
        Lê a linha (única) da tabela balance, com defaults caso ainda não
        exista nenhuma. Pode levantar sqlite3.Error, que quem chamar
        (services/finance.py, services/scheduler.py) deve tratar.

        NAO decide nada sobre o significado dos campos (isso e regra de
        negócio dos services) -- só devolve os 4 campos como estão gravados.
        """
        with self._connection() as conn:
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

    def save_balance_row(
        self,
        amount: Decimal,
        salary: Decimal,
        last_salary_month: Optional[str],
        last_salary_date: Optional[str],
    ) -> None:
        """
        Grava a linha unica da tabela balance, sempre com os 5 campos (para
        nunca apagar acidentalmente algum deles). Pode levantar
        sqlite3.Error.
        """
        with self._connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO balance (id, amount, salary, last_salary_month, last_salary_date) "
                "VALUES (1, ?, ?, ?, ?)",
                (amount, salary, last_salary_month, last_salary_date),
            )
            conn.commit()
