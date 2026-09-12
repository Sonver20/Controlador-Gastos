#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
services/scheduler.py - Serviço de Automação (agendamento de salário).

Responsavel por verificar datas, o ciclo de 30 dias entre creditos de
salario, e decidir quando acionar o credito automatico (add_salary_to_balance).
Também projeta o calendário dos próximos recebimentos (get_salary_calendar),
usando services/payroll.py para o valor liquido de ferias.

Depende apenas de `database.Database` (injetada no construtor) para
persistencia -- nunca executa SQL diretamente.
"""

import sqlite3
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Dict

from database import Database
from .decimal_utils import to_decimal
from .payroll import calcular_ferias


class SchedulerService:
    def __init__(self, db: Database):
        self.db = db

    def get_salary(self) -> Dict[str, Any]:
        """Retorna o salário mensal configurado."""
        try:
            row = self.db.fetch_balance_row()
            return {
                "success": True,
                "salary": row["salary"],
                "last_salary_month": row["last_salary_month"],
                "last_salary_date": row["last_salary_date"],
            }
        except sqlite3.Error as e:
            return {"success": False, "salary": Decimal("0"), "message": str(e)}

    def set_salary(self, amount: Any) -> Dict[str, Any]:
        """Define o valor do salario mensal."""
        try:
            amt = to_decimal(amount)
        except (InvalidOperation, ValueError, TypeError):
            return {"success": False, "message": f"Valor invalido: '{amount}'"}
        try:
            row = self.db.fetch_balance_row()
            self.db.save_balance_row(row["amount"], amt, row["last_salary_month"], row["last_salary_date"])
            return {"success": True, "salary": amt, "message": "Salário configurado."}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Erro ao configurar salário: {e}"}

    def add_salary_to_balance(self) -> Dict[str, Any]:
        """Credita o salario configurado no saldo e registra a data de hoje
        como ultimo credito (ancora do proximo ciclo de 30 dias)."""
        try:
            row = self.db.fetch_balance_row()
            if row["salary"] <= 0:
                return {"success": False, "message": "Salário não configurado."}
            new_balance = row["amount"] + row["salary"]
            today_str = datetime.now().strftime("%Y-%m-%d")
            self.db.save_balance_row(new_balance, row["salary"], row["last_salary_month"], today_str)
            return {
                "success": True,
                "balance": new_balance,
                "salary": row["salary"],
                "message": f"Salário de R$ {row['salary']:.2f} creditado.",
            }
        except sqlite3.Error as e:
            return {"success": False, "message": f"Erro ao creditar salário: {e}"}

    def check_auto_salary(self) -> Dict[str, Any]:
        """Verifica se passaram 30 dias desde o ultimo credito de salario
        e credita automaticamente se for o caso."""
        try:
            res = self.get_salary()
            if res["salary"] <= 0:
                return {"success": True, "should_credit": False, "days_remaining": 0, "message": "Salário não configurado."}

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
        """Marca que o salário já foi creditado neste mês."""
        try:
            row = self.db.fetch_balance_row()
            self.db.save_balance_row(row["amount"], row["salary"], month, row["last_salary_date"])
            return {"success": True}
        except sqlite3.Error as e:
            return {"success": False, "message": str(e)}

    def set_next_salary_date(self, date_str: str) -> Dict[str, Any]:
        """
        Define a PROXIMA data em que o salario deve ser recebido.

        E guardada internamente como last_salary_date = data_informada -
        30 dias, para que tanto o auto-crédito (que dispara 30 dias após
        last_salary_date, em check_auto_salary) quanto o calendario de
        salarios (get_salary_calendar, que projeta a partir dela) fiquem
        consistentes com a mesma data-ancora.
        """
        try:
            next_date = datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            return {"success": False, "message": "Data inválida."}
        anchor = (next_date - timedelta(days=30)).strftime("%Y-%m-%d")
        try:
            row = self.db.fetch_balance_row()
            self.db.save_balance_row(row["amount"], row["salary"], row["last_salary_month"], anchor)
            return {"success": True, "next_salary_date": date_str, "message": "Data de recebimento atualizada."}
        except sqlite3.Error as e:
            return {"success": False, "message": f"Erro ao atualizar data: {e}"}

    def get_salary_calendar(self, vacation_month: int, count: int = 12) -> Dict[str, Any]:
        """
        Retorna as proximas `count` datas de recebimento de salario, cada
        uma exatamente 30 dias após a anterior, a partir de
        last_salary_date. Como os meses tem tamanhos diferentes, 30 dias
        após um recebimento em 15/02 cai em 17/03, não em 15/03 -- a
        "data do mês" deriva do ciclo real, não fica fixa.

        A ocorrencia cujo mes bate com `vacation_month` (1-12) vem com
        is_vacation=True e o valor liquido de ferias (via
        services.payroll.calcular_ferias), em vez do salario bruto. Se
        ainda não houver last_salary_date configurada, retorna lista
        vazia com has_reference_date=False.
        """
        try:
            row = self.db.fetch_balance_row()
            salary = row["salary"]
            anchor_str = row["last_salary_date"]

            if not anchor_str:
                return {"success": True, "data": [], "has_reference_date": False}

            anchor = datetime.strptime(anchor_str, "%Y-%m-%d")
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            # O proprio anchor (last_salary_date) representa o ULTIMO
            # credito, nunca um pagamento futuro valido -- o primeiro
            # candidato e sempre anchor+30. Sem isso, se a "proxima data de
            # recebimento" configurada estiver a mais de 30 dias de hoje,
            # o anchor (= próxima_data - 30) já cairia >= hoje e seria
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
                    entry["label"] = "Não configurado"
                elif is_vacation:
                    ferias = calcular_ferias(salary)
                    entry["amount"] = ferias["salario_liquido"] if ferias.get("success") else None
                    entry["label"] = "Férias (líquido)"
                else:
                    entry["amount"] = salary
                    entry["label"] = "Salário mensal"
                entries.append(entry)

            return {"success": True, "data": entries, "has_reference_date": True}
        except sqlite3.Error as e:
            return {"success": False, "data": [], "message": str(e)}
