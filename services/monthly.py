#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
services/monthly.py - Despesas Mensais (templates de gastos recorrentes).

Um "grupo" de despesa mensal tem nome, categoria, subcategoria opcional e
uma lista de produtos que compartilham essa classificação.

Regra de negócio aqui:
    - Ao aplicar um grupo (manualmente ou automaticamente ao entrar no
      mês corrente), cada item vira uma despesa na tabela `expenses`
      (amount = preco unitario x quantidade) e o total do grupo e
      debitado do saldo, uma unica vez por grupo.
    - `last_applied_month` guarda o mês ("YYYY-MM") da última aplicação;
      `check_and_apply` só aplica grupos cujo mês seja diferente do
      corrente, evitando lançamento duplicado.

Depende de `database.Database` (persistencia) e de `FinanceService`
(ajuste de saldo) -- nunca executa SQL diretamente.
"""

import sqlite3
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from database import Database
from .decimal_utils import to_decimal
from .finance import FinanceService, parse_optional_measure, resolve_amount


class MonthlyService:
    def __init__(self, db: Database, finance: FinanceService):
        self.db = db
        self.finance = finance

    # ------------------------------------------------------------------
    # CRUD de grupos
    # ------------------------------------------------------------------
    def create_group(self, name: str, category: str, subcategory: Optional[str],
                     items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Cria um grupo de despesa mensal com seus itens."""
        clean_name = (name or "").strip()
        if not clean_name:
            return {"success": False, "message": "Informe um nome para a despesa mensal.", "key": "monthly.name_required"}
        clean_category = (category or "").strip()
        if not clean_category:
            return {"success": False, "message": "Informe uma categoria para a despesa mensal.", "key": "monthly.category_required"}
        clean_subcategory = (subcategory or "").strip() or None
        prepared, errors = self._prepare_items(items)
        if not prepared:
            return {"success": False, "message": "Nenhum produto válido. Informe nome, preço e quantidade.", "errors": errors, "key": "monthly.no_valid_items"}
        try:
            group_id = self.db.insert_monthly_group(clean_name, clean_category, clean_subcategory, prepared)
            return {"success": True, "id": group_id, "inserted_items": len(prepared),
                    "message": f"Despesa mensal '{clean_name}' criada com {len(prepared)} item(ns).",
                    "key": "monthly.created", "params": {"name": clean_name, "count": len(prepared)}}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Erro ao criar despesa mensal: {e}", "key": "monthly.create_error", "params": {"error": str(e)}}

    def update_group(self, group_id: int, name: str, category: str, subcategory: Optional[str],
                     items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Atualiza nome e itens de um grupo existente (itens são
        substituídos). Não altera last_applied_month."""
        clean_name = (name or "").strip()
        if not clean_name:
            return {"success": False, "message": "Informe um nome para a despesa mensal.", "key": "monthly.name_required"}
        clean_category = (category or "").strip()
        if not clean_category:
            return {"success": False, "message": "Informe uma categoria para a despesa mensal.", "key": "monthly.category_required"}
        clean_subcategory = (subcategory or "").strip() or None
        prepared, errors = self._prepare_items(items)
        if not prepared:
            return {"success": False, "message": "Nenhum produto válido. Informe nome, preço e quantidade.", "errors": errors, "key": "monthly.no_valid_items"}
        try:
            self.db.update_monthly_group(group_id, clean_name, clean_category, clean_subcategory, prepared)
            return {"success": True, "inserted_items": len(prepared),
                    "message": f"Despesa mensal '{clean_name}' atualizada com {len(prepared)} item(ns).",
                    "key": "monthly.updated", "params": {"name": clean_name, "count": len(prepared)}}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Erro ao atualizar despesa mensal: {e}", "key": "monthly.update_error", "params": {"error": str(e)}}

    def delete_group(self, group_id: int) -> Dict[str, Any]:
        """Exclui um grupo e seus itens (template apenas; despesas já
        lançadas na tabela expenses NÃO são afetadas)."""
        try:
            self.db.delete_monthly_group(group_id)
            return {"success": True, "message": "Despesa mensal excluída.", "key": "monthly.deleted"}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Erro ao excluir: {e}", "key": "monthly.delete_error", "params": {"error": str(e)}}

    def list_groups(self) -> Dict[str, Any]:
        """
        Lista os grupos com seus itens (já com amount calculado) e o
        total do grupo. Mantém last_applied_month para o frontend exibir
        se o grupo já foi lançado no mês corrente.
        """
        try:
            raw_groups = self.db.get_monthly_groups()
            groups = []
            for g in raw_groups:
                items = []
                total = Decimal("0")
                for it in g["items"]:
                    variable_price = bool(it["is_variable_price"])
                    qty, _, amount = resolve_amount(
                        None, it["quantity"], it["unit_price"], variable_price
                    )
                    items.append({
                        "id": it["id"],
                        "description": it["description"],
                        "quantity": qty,
                        "unit_price": it["unit_price"],
                        "is_variable_price": variable_price,
                        "measure_value": it["measure_value"],
                        "measure_unit": it["measure_unit"],
                        "amount": amount,
                    })
                    total += amount
                groups.append({
                    "id": g["id"],
                    "name": g["name"],
                    "category": g["category"],
                    "subcategory": g["subcategory"],
                    "last_applied_month": g["last_applied_month"],
                    "items": items,
                    "total": total,
                })
            return {"success": True, "data": groups}
        except sqlite3.Error as e:
            return {"success": False, "data": [], "message": str(e)}

    # ------------------------------------------------------------------
    # Aplicação (lançar despesas + debitar saldo)
    # ------------------------------------------------------------------
    def apply_group(self, group_id: int, month_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Lança os itens de um grupo como despesas no banco e debita o
        total do saldo. `month_key` (None = mês corrente) é gravado em
        last_applied_month para evitar relançamento automático duplicado.
        """
        if month_key is None:
            month_key = datetime.now().strftime("%Y-%m")

        groups = self.list_groups()
        if not groups["success"]:
            return {"success": False, "message": groups.get("message", "Erro ao carregar grupos.")}
        group = next((g for g in groups["data"] if g["id"] == group_id), None)
        if group is None:
            return {"success": False, "message": "Despesa mensal não encontrada.", "key": "monthly.not_found"}

        rows = []
        for it in group["items"]:
            qty, unit_price, amount = resolve_amount(
                None, it["quantity"], it["unit_price"], it["is_variable_price"]
            )
            rows.append({
                "category": group["category"],
                "subcategory": group["subcategory"],
                "description": it["description"],
                "amount": amount,
                "quantity": qty,
                "unit_price": unit_price,
                "is_variable_price": it["is_variable_price"],
                "measure_value": it["measure_value"],
                "measure_unit": it["measure_unit"],
            })

        batch = self.db.insert_expenses_batch(rows)
        if not batch["success"]:
            return {"success": False, "message": f"Erro ao lançar despesas: {batch.get('message', '')}",
                    "key": "monthly.apply_error", "params": {"error": batch.get("message", "")}}

        self.finance.subtract_from_balance(group["total"])
        self.db.set_monthly_group_applied(group_id, month_key)
        return {
            "success": True,
            "inserted": len(rows),
            "total": group["total"],
            "message": f"'{group['name']}' aplicada: {len(rows)} despesa(s), {group['total']:.2f} debitado(s) do saldo.",
            "key": "monthly.applied",
            "params": {"name": group["name"], "count": len(rows), "total": group["total"]},
        }

    def check_and_apply(self) -> Dict[str, Any]:
        """
        Aplica automaticamente os grupos pendentes do mês corrente
        (grupos cujo last_applied_month seja diferente de "YYYY-MM" de
        hoje). Chamado na inicialização do app.
        """
        current_month = datetime.now().strftime("%Y-%m")
        groups = self.list_groups()
        if not groups["success"]:
            return {"success": False, "applied_count": 0, "message": groups.get("message", "")}

        applied = []
        for g in groups["data"]:
            if g["last_applied_month"] == current_month:
                continue
            res = self.apply_group(g["id"], month_key=current_month)
            if res["success"]:
                applied.append(res)

        if not applied:
            return {"success": True, "applied_count": 0, "message": "Nenhuma despesa mensal pendente.", "key": "monthly.none_pending"}

        total = sum((r["total"] for r in applied), Decimal("0"))
        total_inserted = sum(r["inserted"] for r in applied)
        return {
            "success": True,
            "applied_count": len(applied),
            "inserted": total_inserted,
            "total": total,
            "message": f"Despesas mensais lançadas: {len(applied)} grupo(s), {total_inserted} despesa(s), {total:.2f} debitado(s) do saldo.",
            "key": "monthly.check_applied",
            "params": {"groups": len(applied), "inserted": total_inserted, "total": total},
        }

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _prepare_items(items: List[Dict[str, Any]]):
        """
        Valida e normaliza produtos sem classificação individual.
        Retorna (rows_prontos, errors).
        """
        rows = []
        errors = []
        for item in items or []:
            description = str(item.get("description", "")).strip()
            if not description:
                errors.append(f"Produto sem nome: {item}")
                continue
            try:
                variable_price = bool(item.get("is_variable_price", False))
                entered_price = to_decimal(item.get("unit_price"))
                qty, normalized_price, amount = resolve_amount(
                    None, item.get("quantity"), entered_price, variable_price
                )
                measure_value, measure_unit = parse_optional_measure(
                    item.get("measure_value"), item.get("measure_unit")
                )
            except (InvalidOperation, ValueError, TypeError):
                errors.append(f"Preço, quantidade ou medida inválidos: {item}")
                continue
            if amount <= 0:
                errors.append(f"Valor zerado ou negativo: {item}")
                continue
            rows.append({
                "description": description,
                "quantity": qty,
                "unit_price": entered_price if variable_price else normalized_price,
                "is_variable_price": variable_price,
                "measure_value": measure_value,
                "measure_unit": measure_unit,
            })
        return rows, errors
