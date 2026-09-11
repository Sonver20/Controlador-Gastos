#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py - Main entry point for Controlador de Gastos (Desktop)
"""

import os
from decimal import Decimal
from functools import wraps

import webview
from database import Database
from config import Config
from version import APP_VERSION


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def asset_path(filename: str) -> str:
    return os.path.join(BASE_DIR, filename)


def _jsonify(value):
    """
    Converte recursivamente qualquer `Decimal` em string antes de cruzar a
    ponte pywebview -> JS, ja que `json.dumps` (usado internamente pelo
    pywebview) nao sabe serializar Decimal. O formato usado (sem notacao
    cientifica, via `format(d, "f")`) preserva o valor exato digitado;
    o JS so precisa converter isso para Number na hora de formatar/exibir.
    """
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, dict):
        return {k: _jsonify(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonify(v) for v in value]
    return value


def jsonify_result(func):
    """Decorator que aplica _jsonify ao retorno de um metodo da Api."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return _jsonify(func(*args, **kwargs))
    return wrapper


class Api:
    def __init__(self):
        self.db = Database(db_path=asset_path("gastos.db"))
        self.cfg = Config(config_path=asset_path("app_config.json"))

    def get_app_version(self):
        return {"success": True, "version": APP_VERSION}

    def get_theme(self):
        return self.cfg.get_theme()

    def set_theme(self, theme: str):
        return self.cfg.set_theme(theme)

    @jsonify_result
    def get_balance(self):
        return self.db.get_balance()

    @jsonify_result
    def set_balance(self, amount):
        return self.db.set_balance(amount)

    @jsonify_result
    def get_salary(self):
        return self.db.get_salary()

    @jsonify_result
    def set_salary(self, amount):
        return self.db.set_salary(amount)

    @jsonify_result
    def add_salary_to_balance(self):
        return self.db.add_salary_to_balance()

    @jsonify_result
    def check_auto_salary(self):
        return self.db.check_auto_salary()

    @jsonify_result
    def calcular_ferias(self, salario_bruto):
        return Database.calcular_ferias(salario_bruto)

    def set_last_salary_month(self, month: str):
        return self.db.set_last_salary_month(month)

    @jsonify_result
    def set_next_salary_date(self, date_str: str):
        return self.db.set_next_salary_date(date_str)

    @jsonify_result
    def get_salary_calendar(self):
        vacation_month = self.cfg.get("vacation_month", 7)
        return self.db.get_salary_calendar(vacation_month)

    def get_vacation_month(self):
        return {"success": True, "month": self.cfg.get("vacation_month", 7)}

    def set_vacation_month(self, month: int):
        return self.cfg.set("vacation_month", int(month))

    @jsonify_result
    def add_expense(self, category: str, description: str, amount=None, subcategory=None, quantity=None, unit_price=None):
        res = self.db.add_expense(category, description, amount, subcategory, quantity, unit_price)
        if res["success"]:
            # Usa o valor calculado (amt), nao o parametro cru -- importante
            # no modo quantidade x preco unitario, onde 'amount' nem chega
            # a ser informado pelo frontend.
            self.db.subtract_from_balance(res["amount"])
        return res

    @jsonify_result
    def add_expenses_bulk(self, category: str, lines: str):
        res = self.db.add_expenses_bulk(category, lines)
        # Usa o total exato ja calculado pelo database.py (Decimal, soma
        # apenas das linhas realmente inseridas), em vez de reprocessar o
        # texto aqui de novo -- evita divergencia e erro de arredondamento.
        if res["success"] and res["inserted"] > 0 and res.get("total", 0) > 0:
            self.db.subtract_from_balance(res["total"])
        return res

    @jsonify_result
    def add_expenses_structured(self, category: str, subcategory, products: list):
        """
        Nova Despesa unificada: uma categoria/subcategoria compartilhada e
        uma lista de produtos (nome + preco unitario + quantidade). Isso
        substitui o antigo Cadastro em Massa (texto colado) no frontend.
        """
        res = self.db.add_expenses_structured(category, subcategory, products)
        if res["success"] and res["inserted"] > 0 and res.get("total", 0) > 0:
            self.db.subtract_from_balance(res["total"])
        return res

    @jsonify_result
    def get_months_summary(self):
        return self.db.get_months_summary()

    @jsonify_result
    def get_categories_by_month(self, month: str):
        return self.db.get_categories_by_month(month)

    @jsonify_result
    def get_expenses_by_month_and_category(self, month: str, category: str, subcategory=None):
        return self.db.get_expenses_by_month_and_category(month, category, subcategory)

    @jsonify_result
    def get_subcategories_by_month_and_category(self, month: str, category: str):
        return self.db.get_subcategories_by_month_and_category(month, category)

    @jsonify_result
    def get_expense(self, expense_id: int):
        return self.db.get_expense(expense_id)

    @jsonify_result
    def update_expense(self, expense_id: int, category: str, description: str, amount=None, subcategory=None, quantity=None, unit_price=None, date_str=None):
        # BUG CORRIGIDO: editar uma despesa (ex.: aumentar o preco de um
        # produto) nao ajustava o saldo. Agora calculamos a diferenca entre
        # o valor antigo e o novo e aplicamos via subtract_from_balance:
        # se o valor aumentou, desconta mais do saldo; se diminuiu,
        # devolve a diferenca (delta negativo vira soma dentro dela).
        existing = self.db.get_expense(expense_id)
        old_amount = existing["data"]["amount"] if existing.get("success") else None

        res = self.db.update_expense(expense_id, category, description, amount, subcategory, quantity, unit_price, date_str)

        if res["success"] and old_amount is not None:
            delta = res["amount"] - old_amount
            if delta != 0:
                self.db.subtract_from_balance(delta)
        return res

    def delete_expense(self, expense_id: int):
        return self.db.delete_expense(expense_id)

    def get_all_categories(self):
        return self.db.get_all_categories()

    def get_all_subcategories(self):
        return self.db.get_all_subcategories()

    @jsonify_result
    def parse_raw_text(self, raw_text: str):
        return self.db.parse_raw_text(raw_text)

    @jsonify_result
    def save_parsed_expenses(self, category: str, parsed_list: list):
        res = self.db.save_parsed_expenses(category, parsed_list)
        # Mesma logica do bulk: soma apenas o que foi de fato inserido.
        if res["success"] and res["inserted"] > 0 and res.get("total", 0) > 0:
            self.db.subtract_from_balance(res["total"])
        return res


if __name__ == "__main__":
    api = Api()
    webview.create_window(
        title="Controlador de Gastos",
        url=asset_path("index.html"),
        js_api=api,
        width=1100,
        height=750,
        min_size=(900, 600),
        resizable=True,
        text_select=True,
    )
    webview.start(debug=False, gui="gtk")
