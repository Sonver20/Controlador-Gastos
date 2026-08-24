#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py - Main entry point for Controlador de Gastos (Desktop)
"""

import os
import webview
from database import Database
from config import Config


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def asset_path(filename: str) -> str:
    return os.path.join(BASE_DIR, filename)


class Api:
    def __init__(self):
        self.db = Database(db_path=asset_path("gastos.db"))
        self.cfg = Config(config_path=asset_path("app_config.json"))

    def get_theme(self):
        return self.cfg.get_theme()

    def set_theme(self, theme: str):
        return self.cfg.set_theme(theme)

    def get_balance(self):
        return self.db.get_balance()

    def set_balance(self, amount: float):
        return self.db.set_balance(amount)

    def get_salary(self):
        return self.db.get_salary()

    def set_salary(self, amount: float):
        return self.db.set_salary(amount)

    def add_salary_to_balance(self):
        return self.db.add_salary_to_balance()

    def set_last_salary_month(self, month: str):
        return self.db.set_last_salary_month(month)

    def add_expense(self, category: str, description: str, amount: float):
        res = self.db.add_expense(category, description, amount)
        if res["success"]:
            self.db.subtract_from_balance(amount)
        return res

    def add_expenses_bulk(self, category: str, lines: str):
        res = self.db.add_expenses_bulk(category, lines)
        if res["success"] and res["inserted"] > 0:
            total = 0.0
            for line in lines.strip().splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = [p.strip() for p in line.rsplit(",", 1)]
                if len(parts) == 2:
                    val_str = parts[1].replace("R$", "").replace("$", "").strip().replace(",", ".")
                    try:
                        total += float(val_str)
                    except ValueError:
                        pass
            if total > 0:
                self.db.subtract_from_balance(total)
        return res

    def get_months_summary(self):
        return self.db.get_months_summary()

    def get_categories_by_month(self, month: str):
        return self.db.get_categories_by_month(month)

    def get_expenses_by_month_and_category(self, month: str, category: str):
        return self.db.get_expenses_by_month_and_category(month, category)

    def get_expense(self, expense_id: int):
        return self.db.get_expense(expense_id)

    def update_expense(self, expense_id: int, category: str, description: str, amount: float):
        return self.db.update_expense(expense_id, category, description, amount)

    def delete_expense(self, expense_id: int):
        return self.db.delete_expense(expense_id)

    def get_all_categories(self):
        return self.db.get_all_categories()

    def parse_raw_text(self, raw_text: str):
        return self.db.parse_raw_text(raw_text)

    def save_parsed_expenses(self, category: str, parsed_list: list):
        res = self.db.save_parsed_expenses(category, parsed_list)
        if res["success"] and res["inserted"] > 0:
            total = sum(item.get("amount", 0) for item in parsed_list)
            if total > 0:
                self.db.subtract_from_balance(total)
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
