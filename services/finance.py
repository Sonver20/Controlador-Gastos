#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
services/finance.py - Servico Financeiro / Regra de Negocio.

Responsavel por:
    - Gerenciar o saldo (consultar, definir, ajustar).
    - Garantir que toda inserção, edição ou exclusão de despesa ajuste o
      saldo corretamente (inclusive exclusao: excluir uma despesa devolve
      o valor dela ao saldo, o inverso de registra-la).
    - Decidir "como calcular o valor de uma despesa" (preco unitario x
      quantidade, via resolve_amount) -- o database.py só grava valores
      já prontos, nunca calcula isso.
    - Processar listas de despesas vindas do parser de texto, do cadastro
      em massa (texto colado) e do formulario estruturado de Nova Despesa.

Depende apenas de `database.Database` (injetada no construtor) para
persistencia -- nunca executa SQL diretamente.
"""

import re
import sqlite3
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

from .decimal_utils import to_decimal, to_quantity, TWO_PLACES
from database import Database


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


class FinanceService:
    def __init__(self, db: Database):
        self.db = db

    # ------------------------------------------------------------------
    # Preparação de campos (compartilhado por add/update)
    # ------------------------------------------------------------------
    def _prepare_expense_fields(self, category: str, description: str, amount: Any,
                                 subcategory: Optional[str], quantity: Any, unit_price: Any):
        """
        Resolve os campos de uma despesa antes de gravar: calcula o valor
        final (direto, ou preco unitario x quantidade) e normaliza
        categoria/subcategoria/descrição. Pode levantar
        InvalidOperation/ValueError/TypeError para entradas invalidas.
        """
        qty, price, amt = resolve_amount(amount, quantity, unit_price)
        sub = (subcategory or "").strip() or None
        return category.strip(), sub, description.strip(), amt, qty, price

    # ------------------------------------------------------------------
    # Saldo
    # ------------------------------------------------------------------
    def get_balance(self) -> Dict[str, Any]:
        """Retorna o saldo atual da conta."""
        try:
            row = self.db.fetch_balance_row()
            return {"success": True, "balance": row["amount"], "last_salary_date": row["last_salary_date"]}
        except sqlite3.Error as e:
            return {"success": False, "balance": Decimal("0"), "message": str(e)}

    def set_balance(self, amount: Any) -> Dict[str, Any]:
        """Define o saldo da conta (sobrescreve), preservando o salario."""
        try:
            amt = to_decimal(amount)
        except (InvalidOperation, ValueError, TypeError):
            return {"success": False, "message": f"Valor inválido: '{amount}'", "key": "validation.invalid_value", "params": {"value": str(amount)}}
        try:
            row = self.db.fetch_balance_row()
            self.db.save_balance_row(amt, row["salary"], row["last_salary_month"], row["last_salary_date"])
            return {"success": True, "balance": amt, "message": "Saldo atualizado.", "key": "balance.updated"}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Erro ao atualizar saldo: {e}", "key": "balance.update_error", "params": {"error": str(e)}}

    def subtract_from_balance(self, amount: Any) -> Dict[str, Any]:
        """Subtrai `amount` do saldo (preserva salario e demais campos).
        Um `amount` negativo, na pratica, ADICIONA ao saldo -- usado por
        delete_expense para devolver o valor de uma despesa excluida."""
        try:
            amt = to_decimal(amount)
        except (InvalidOperation, ValueError, TypeError):
            return {"success": False, "message": f"Valor inválido: '{amount}'"}
        try:
            row = self.db.fetch_balance_row()
            new_balance = row["amount"] - amt
            self.db.save_balance_row(new_balance, row["salary"], row["last_salary_month"], row["last_salary_date"])
            return {"success": True, "balance": new_balance, "message": f"Saldo: {new_balance:.2f}"}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Erro ao subtrair saldo: {e}"}

    # ------------------------------------------------------------------
    # Despesas: CRUD com ajuste de saldo
    # ------------------------------------------------------------------
    def add_expense(self, category: str, description: str, amount: Any = None,
                     subcategory: Optional[str] = None, quantity: Any = None,
                     unit_price: Any = None) -> Dict[str, Any]:
        """Registra uma despesa e desconta o valor calculado do saldo."""
        try:
            cat, sub, desc, amt, qty, price = self._prepare_expense_fields(
                category, description, amount, subcategory, quantity, unit_price
            )
        except (InvalidOperation, ValueError, TypeError):
            return {"success": False, "id": None, "message": f"Valor inválido: '{amount}'", "key": "validation.invalid_value", "params": {"value": str(amount)}}

        res = self.db.insert_expense(cat, sub, desc, amt, qty, price)
        if res["success"]:
            res["amount"] = amt
            self.subtract_from_balance(amt)
        return res

    def update_expense(self, expense_id: int, category: str, description: str, amount: Any = None,
                        subcategory: Optional[str] = None, quantity: Any = None, unit_price: Any = None,
                        date_str: Optional[str] = None) -> Dict[str, Any]:
        """
        Atualiza uma despesa. Se o valor mudou (por editar preco e/ou
        quantidade), ajusta o saldo pela DIFERENCA entre o valor antigo e
        o novo -- se subiu, desconta mais; se baixou, devolve a diferenca.

        `date_str`, se informado ("YYYY-MM-DD"), atualiza a data da
        despesa preservando o horario original.
        """
        try:
            cat, sub, desc, amt, qty, price = self._prepare_expense_fields(
                category, description, amount, subcategory, quantity, unit_price
            )
        except (InvalidOperation, ValueError, TypeError):
            return {"success": False, "message": f"Valor inválido: '{amount}'", "key": "validation.invalid_value", "params": {"value": str(amount)}}

        if date_str is not None:
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                return {"success": False, "message": "Data inválida.", "key": "validation.invalid_date"}

        existing = self.db.get_expense(expense_id)
        if not existing.get("success"):
            return {"success": False, "message": "Despesa não encontrada para atualizar.", "key": "expense.not_found"}
        old_amount = existing["data"]["amount"]

        created_at = None
        if date_str is not None:
            old_created_at = existing["data"]["created_at"] or ""
            time_part = old_created_at.split(" ", 1)[1] if " " in old_created_at else "00:00:00"
            created_at = f"{date_str} {time_part}"

        res = self.db.update_expense_row(expense_id, cat, sub, desc, amt, qty, price, created_at)
        if res["success"]:
            res["amount"] = amt
            delta = amt - old_amount
            if delta != 0:
                self.subtract_from_balance(delta)
        return res

    def delete_expense(self, expense_id: int) -> Dict[str, Any]:
        """
        Exclui a despesa e DEVOLVE o valor dela ao saldo -- o inverso de
        registrar uma despesa, para manter o saldo consistente com o
        que realmente foi ajustado ao editar (delta) e ao adicionar.
        """
        existing = self.db.get_expense(expense_id)
        old_amount = existing["data"]["amount"] if existing.get("success") else None

        res = self.db.delete_expense_row(expense_id)
        if res["success"] and old_amount is not None:
            self.subtract_from_balance(-old_amount)
        return res

    # ------------------------------------------------------------------
    # Processamento de listas de despesas (parser / massa / estruturado)
    # ------------------------------------------------------------------
    def add_expenses_bulk(self, category: str, lines: str) -> Dict[str, Any]:
        """Cadastro em massa: linhas no formato 'Descrição, Valor'."""
        inserted = 0
        errors: List[str] = []
        total = Decimal("0")
        category = category.strip()
        rows = []

        for line in lines.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",", 1)]
            if len(parts) != 2:
                errors.append(f"Formato inválido: '{line}'")
                continue
            desc, val_str = parts
            try:
                cleaned = val_str.replace("R$", "").replace("$", "").strip().replace(",", ".")
                amount = to_decimal(cleaned)
            except (InvalidOperation, ValueError):
                errors.append(f"Valor inválido: '{val_str}'")
                continue
            rows.append({
                "category": category, "subcategory": None, "description": desc,
                "amount": amount, "quantity": Decimal("1"), "unit_price": amount,
            })
            inserted += 1
            total += amount

        batch = self.db.insert_expenses_batch(rows)
        if not batch["success"]:
            return {"success": False, "inserted": 0, "errors": errors, "total": Decimal("0"),
                    "message": f"Erro em massa: {batch.get('message', '')}",
                    "key": "expenses.batch.error", "params": {"error": batch.get("message", "")}}

        msg = f"{inserted} despesa(s) inserida(s)."
        if errors:
            msg += f" {len(errors)} erro(s) encontrado(s)."
        if inserted > 0 and total > 0:
            self.subtract_from_balance(total)
        return {"success": True, "inserted": inserted, "errors": errors, "total": total, "message": msg,
                "key": "expenses.bulk.result", "params": {"inserted": inserted, "errors_count": len(errors)}}

    def add_expenses_structured(self, category: str, subcategory: Optional[str],
                                 products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Nova Despesa unificada: uma categoria/subcategoria compartilhada e
        uma lista de produtos (nome, preco unitario, quantidade). `products`:
        lista de dicts com "description", "unit_price" e "quantity".
        """
        inserted = 0
        errors: List[str] = []
        total = Decimal("0")
        cat = category.strip()
        sub = (subcategory or "").strip() or None
        rows = []

        for item in products:
            desc = str(item.get("description", "")).strip()
            try:
                qty, price, amt = resolve_amount(None, item.get("quantity"), item.get("unit_price"))
            except (InvalidOperation, ValueError, TypeError):
                errors.append(f"Dados inválidos: {item}")
                continue
            if not desc or amt <= 0:
                errors.append(f"Dados inválidos: {item}")
                continue
            rows.append({
                "category": cat, "subcategory": sub, "description": desc,
                "amount": amt, "quantity": qty, "unit_price": price,
            })
            inserted += 1
            total += amt

        batch = self.db.insert_expenses_batch(rows)
        if not batch["success"]:
            return {"success": False, "inserted": 0, "errors": errors, "total": Decimal("0"),
                    "message": batch.get("message", ""),
                    "key": "expenses.batch.error", "params": {"error": batch.get("message", "")}}

        if inserted > 0 and total > 0:
            self.subtract_from_balance(total)
        return {"success": True, "inserted": inserted, "errors": errors, "total": total,
                "message": f"{inserted} despesa(s) registrada(s).",
                "key": "expenses.structured.result", "params": {"inserted": inserted}}
