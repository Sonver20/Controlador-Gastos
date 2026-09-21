#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py - Main entry point for Controlador de Gastos (Desktop)

A classe Api e a ponte entre o frontend (JS, via pywebview) e o backend.
Ela não contém regra de negócio: para leituras simples (sem cálculo ou
efeito colateral) chama database.py diretamente; para qualquer operação
com regra de negocio (saldo, valor de despesa, calendario de salario,
impostos), delega para o servico correspondente em services/.
"""

import os
from decimal import Decimal
from functools import wraps

import webview
from database import Database
from config import Config
from version import APP_VERSION
from services.finance import FinanceService
from services.scheduler import SchedulerService
from services.monthly import MonthlyService
from services.payroll import calcular_ferias


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def asset_path(filename: str) -> str:
    return os.path.join(BASE_DIR, filename)


def _jsonify(value):
    """
    Converte recursivamente qualquer `Decimal` em string antes de cruzar a
    ponte pywebview -> JS, já que `json.dumps` (usado internamente pelo
    pywebview) não sabe serializar Decimal. O formato usado (sem notação
    cientifica, via `format(d, "f")`) preserva o valor exato digitado;
    o JS só precisa converter isso para Number na hora de formatar/exibir.
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
        self.finance = FinanceService(self.db)
        self.scheduler = SchedulerService(self.db)
        self.monthly = MonthlyService(self.db, self.finance)

    def get_app_version(self):
        return {"success": True, "version": APP_VERSION}

    def get_theme(self):
        return self.cfg.get_theme()

    def set_theme(self, theme: str):
        return self.cfg.set_theme(theme)

    # ------------------------------------------------------------------
    # Saldo (services/finance.py)
    # ------------------------------------------------------------------
    @jsonify_result
    def get_balance(self):
        return self.finance.get_balance()

    @jsonify_result
    def set_balance(self, amount):
        return self.finance.set_balance(amount)

    # ------------------------------------------------------------------
    # Salário / calendário (services/scheduler.py)
    # ------------------------------------------------------------------
    @jsonify_result
    def get_salary(self):
        return self.scheduler.get_salary()

    @jsonify_result
    def set_salary(self, amount):
        return self.scheduler.set_salary(amount)

    @jsonify_result
    def add_salary_to_balance(self):
        return self.scheduler.add_salary_to_balance()

    @jsonify_result
    def check_auto_salary(self):
        return self.scheduler.check_auto_salary()

    def set_last_salary_month(self, month: str):
        return self.scheduler.set_last_salary_month(month)

    @jsonify_result
    def set_next_salary_date(self, date_str: str):
        return self.scheduler.set_next_salary_date(date_str)

    @jsonify_result
    def get_salary_calendar(self):
        vacation_month = self.cfg.get("vacation_month", 7)
        return self.scheduler.get_salary_calendar(vacation_month)

    def get_vacation_month(self):
        return {"success": True, "month": self.cfg.get("vacation_month", 7)}

    def set_vacation_month(self, month: int):
        return self.cfg.set("vacation_month", int(month))

    # ------------------------------------------------------------------
    # Férias / tributos (services/payroll.py)
    # ------------------------------------------------------------------
    @jsonify_result
    def calcular_ferias(self, salario_bruto):
        return calcular_ferias(salario_bruto)

    # ------------------------------------------------------------------
    # Despesas: escrita com ajuste de saldo (services/finance.py)
    # ------------------------------------------------------------------
    @jsonify_result
    def add_expense(self, category: str, description: str, amount=None, subcategory=None, quantity=None, unit_price=None):
        return self.finance.add_expense(category, description, amount, subcategory, quantity, unit_price)

    @jsonify_result
    def add_expenses_bulk(self, category: str, lines: str):
        return self.finance.add_expenses_bulk(category, lines)

    @jsonify_result
    def add_expenses_structured(self, category: str, subcategory, products: list):
        """
        Nova Despesa unificada: uma categoria/subcategoria compartilhada e
        uma lista de produtos (nome + preco unitario + quantidade). Isso
        substitui o antigo Cadastro em Massa (texto colado) no frontend.
        """
        return self.finance.add_expenses_structured(category, subcategory, products)

    @jsonify_result
    def update_expense(self, expense_id: int, category: str, description: str, amount=None, subcategory=None, quantity=None, unit_price=None, date_str=None):
        return self.finance.update_expense(expense_id, category, description, amount, subcategory, quantity, unit_price, date_str)

    @jsonify_result
    def delete_expense(self, expense_id: int):
        return self.finance.delete_expense(expense_id)

    @jsonify_result
    def parse_raw_text(self, raw_text: str):
        return self.finance.parse_raw_text(raw_text)

    @jsonify_result
    def save_parsed_expenses(self, category: str, parsed_list: list):
        return self.finance.save_parsed_expenses(category, parsed_list)

    # ------------------------------------------------------------------
    # Despesas Mensais (services/monthly.py) — templates recorrentes
    # ------------------------------------------------------------------
    @jsonify_result
    def get_monthly_groups(self):
        return self.monthly.list_groups()

    @jsonify_result
    def save_monthly_group(self, name: str, items: list, group_id=None):
        if group_id is not None:
            return self.monthly.update_group(int(group_id), name, items)
        return self.monthly.create_group(name, items)

    @jsonify_result
    def delete_monthly_group(self, group_id: int):
        return self.monthly.delete_group(int(group_id))

    @jsonify_result
    def apply_monthly_group(self, group_id: int):
        return self.monthly.apply_group(int(group_id))

    @jsonify_result
    def check_monthly_expenses(self):
        return self.monthly.check_and_apply()

    # ------------------------------------------------------------------
    # Despesas: leitura pura (database.py direto -- sem regra de negocio)
    # ------------------------------------------------------------------
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

    def get_all_categories(self):
        return self.db.get_all_categories()

    def get_all_subcategories(self):
        return self.db.get_all_subcategories()


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
