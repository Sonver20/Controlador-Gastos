"""
tests/test_salary.py - Salário, ciclo de 30 dias e calendário de recebimentos.
"""

import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from database import Database
from services.finance import FinanceService
from services.scheduler import SchedulerService


class TestDatabaseSalary(unittest.TestCase):
    """Testa operacoes de salario mensal."""

    def setUp(self):
        self.db = Database(db_path=":memory:")
        self.finance = FinanceService(self.db)
        self.scheduler = SchedulerService(self.db)

    def test_get_salary_default_zero(self):
        res = self.scheduler.get_salary()
        self.assertTrue(res["success"])
        self.assertEqual(res["salary"], Decimal("0"))
        self.assertIsNone(res["last_salary_month"])

    def test_set_salary(self):
        res = self.scheduler.set_salary(5000.0)
        self.assertTrue(res["success"])
        self.assertEqual(res["salary"], Decimal("5000.00"))
        fetched = self.scheduler.get_salary()
        self.assertEqual(fetched["salary"], Decimal("5000.00"))

    def test_set_salary_preserves_balance(self):
        self.finance.set_balance(1000.0)
        self.scheduler.set_salary(5000.0)
        balance = self.finance.get_balance()
        self.assertEqual(balance["balance"], Decimal("1000.00"))

    def test_add_salary_to_balance(self):
        self.finance.set_balance(1000.0)
        self.scheduler.set_salary(5000.0)
        res = self.scheduler.add_salary_to_balance()
        self.assertTrue(res["success"])
        self.assertEqual(res["balance"], Decimal("6000.00"))
        self.assertEqual(res["salary"], Decimal("5000.00"))

    def test_add_salary_to_balance_no_salary_configured(self):
        res = self.scheduler.add_salary_to_balance()
        self.assertFalse(res["success"])
        self.assertIn("não configurado", res["message"].lower())

    def test_add_salary_to_balance_zero_salary(self):
        self.scheduler.set_salary(0.0)
        res = self.scheduler.add_salary_to_balance()
        self.assertFalse(res["success"])

    def test_set_last_salary_month(self):
        # Precisa criar registro na tabela balance primeiro
        self.finance.set_balance(0.0)
        res = self.scheduler.set_last_salary_month("2026-08")
        self.assertTrue(res["success"])
        salary = self.scheduler.get_salary()
        self.assertEqual(salary["last_salary_month"], "2026-08")

    def test_add_salary_multiple_times(self):
        self.scheduler.set_salary(3000.0)
        self.scheduler.add_salary_to_balance()
        self.scheduler.add_salary_to_balance()
        balance = self.finance.get_balance()
        self.assertEqual(balance["balance"], Decimal("6000.00"))


class TestSalaryCalendar(unittest.TestCase):
    """
    Testa a correcao do calendario de salario: em vez de assumir o mesmo
    dia do mes para todos os recebimentos, projeta a partir de uma data-
    ancora configuravel, avancando exatamente 30 dias por ciclo (o que faz
    o dia mudar de mes para mes, ja que nem todo mes tem o mesmo tamanho).
    """

    def setUp(self):
        self.db = Database(db_path=":memory:")
        self.finance = FinanceService(self.db)
        self.scheduler = SchedulerService(self.db)

    def test_set_next_salary_date_stores_anchor_30_days_before(self):
        res = self.scheduler.set_next_salary_date("2026-03-17")
        self.assertTrue(res["success"])
        salary = self.scheduler.get_salary()
        self.assertEqual(salary["last_salary_date"], "2026-02-15")

    def test_set_next_salary_date_invalid_format(self):
        res = self.scheduler.set_next_salary_date("17/03/2026")
        self.assertFalse(res["success"])

    def test_set_next_salary_date_preserves_balance_and_salary(self):
        self.finance.set_balance("1000.00")
        self.scheduler.set_salary("5000.00")
        self.scheduler.set_next_salary_date("2026-03-17")
        self.assertEqual(self.finance.get_balance()["balance"], Decimal("1000.00"))
        self.assertEqual(self.scheduler.get_salary()["salary"], Decimal("5000.00"))

    def test_calendar_without_reference_date(self):
        self.scheduler.set_salary("3000.00")
        cal = self.scheduler.get_salary_calendar(vacation_month=7)
        self.assertTrue(cal["success"])
        self.assertFalse(cal["has_reference_date"])
        self.assertEqual(cal["data"], [])

    def test_calendar_dates_are_exactly_30_days_apart(self):
        """O nucleo da correcao: cada data deve ser exatamente 30 dias
        apos a anterior, nao 'o mesmo dia do proximo mes'."""
        self.scheduler.set_salary("3000.00")
        self.scheduler.set_next_salary_date("2026-09-15")
        cal = self.scheduler.get_salary_calendar(vacation_month=1, count=6)
        self.assertTrue(cal["has_reference_date"])
        dates = [datetime.strptime(e["date"], "%Y-%m-%d") for e in cal["data"]]
        for i in range(1, len(dates)):
            self.assertEqual((dates[i] - dates[i - 1]).days, 30)

    def test_calendar_feb_to_march_drifts_correctly(self):
        """Caso especifico da reclamacao original: recebendo em 15/02, o
        proximo ciclo cai bem depois do dia 15 de marco (nao no mesmo dia).
        Usa uma data no futuro (2027) para nao ser adiantada para "hoje"
        pela logica de projecao (isso e testado separadamente em
        test_calendar_projects_forward_from_past_anchor)."""
        self.scheduler.set_salary("3000.00")
        self.scheduler.set_next_salary_date("2027-02-15")
        cal = self.scheduler.get_salary_calendar(vacation_month=1, count=2)
        first, second = cal["data"][0]["date"], cal["data"][1]["date"]
        self.assertEqual(first, "2027-02-15")
        # 15/02/2027 + 30 dias = 17/03/2027 (2027 nao e bissexto: fev tem 28 dias)
        self.assertEqual(second, "2027-03-17")

    def test_calendar_marks_vacation_month_with_net_amount(self):
        self.scheduler.set_salary("5000.00")
        self.scheduler.set_next_salary_date("2026-09-15")
        cal = self.scheduler.get_salary_calendar(vacation_month=10, count=3)
        vacation_entries = [e for e in cal["data"] if e["is_vacation"]]
        self.assertEqual(len(vacation_entries), 1)
        self.assertEqual(vacation_entries[0]["label"], "Férias (líquido)")
        # o valor liquido de ferias deve ser diferente do salario bruto
        self.assertNotEqual(vacation_entries[0]["amount"], Decimal("5000.00"))

    def test_calendar_no_salary_configured_shows_none_amount(self):
        self.scheduler.set_next_salary_date("2026-09-15")
        cal = self.scheduler.get_salary_calendar(vacation_month=7, count=2)
        for e in cal["data"]:
            self.assertIsNone(e["amount"])
            self.assertEqual(e["label"], "Não configurado")

    def test_calendar_projects_forward_from_past_anchor(self):
        """Se a ancora estiver no passado, a lista deve comecar na
        primeira ocorrencia igual ou posterior a hoje, nao no passado."""
        self.scheduler.set_salary("3000.00")
        self.scheduler.set_next_salary_date("2020-01-15")  # bem no passado
        cal = self.scheduler.get_salary_calendar(vacation_month=7, count=1)
        first_date = datetime.strptime(cal["data"][0]["date"], "%Y-%m-%d")
        self.assertGreaterEqual(first_date, datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))

    def test_calendar_future_next_date_beyond_30_days_shown_exactly(self):
        """Bug corrigido: se a 'proxima data de recebimento' configurada
        estiver a MAIS de 30 dias de hoje, o primeiro item do calendario
        tem que ser exatamente essa data -- e nao um ciclo (30 dias) antes
        dela. O erro acontecia porque a ancora interna (next_date - 30)
        ja caia no futuro e era exibida diretamente, sem avancar +30."""
        self.scheduler.set_salary("3000.00")
        far_future = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
        self.scheduler.set_next_salary_date(far_future)
        cal = self.scheduler.get_salary_calendar(vacation_month=1, count=1)
        self.assertEqual(cal["data"][0]["date"], far_future)
