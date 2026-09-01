"""Regras de cálculo puras (sem I/O). Ver documento de desenho, seção 05."""
import math
from datetime import date

from .dates import add_months


# ---- Dashboard ----
def savings_rate(receitas, despesas):
    """(Receitas - Despesas de consumo) / Receitas * 100."""
    if not receitas:
        return 0.0
    return (receitas - despesas) / receitas * 100


def free_balance(receitas, despesas, aportes):
    """Saldo livre = Receitas - Despesas - Aportes."""
    return receitas - despesas - aportes


# ---- Orçamento ----
def budget_usage(gasto, planejado):
    if not planejado:
        return 0.0
    return gasto / planejado * 100


def budget_projection(gasto, day_of_month, total_days):
    """Projeção de fechamento = média diária * dias do mês."""
    if not day_of_month:
        return gasto
    return gasto / day_of_month * total_days


def budget_status_label(usage_pct):
    if usage_pct > 100:
        return "over"     # acima do orçamento
    if usage_pct >= 80:
        return "warn"     # atenção
    return "ok"           # normal


# ---- Metas ----
def goal_remaining(target, current):
    return max((target or 0) - (current or 0), 0)


def goal_pct(target, current):
    if not target:
        return 0.0
    return min((current or 0) / target * 100, 100)


def months_until(target_date, from_date=None):
    from_date = from_date or date.today()
    if not target_date:
        return None
    return max((target_date.year - from_date.year) * 12 + (target_date.month - from_date.month), 0)


def monthly_needed(remaining, months):
    if not months or months <= 0:
        return remaining
    return remaining / months


def months_to_complete(remaining, monthly):
    if not monthly or monthly <= 0:
        return None
    return math.ceil(remaining / monthly)


def estimated_date(remaining, monthly, from_date=None):
    from_date = from_date or date.today()
    m = months_to_complete(remaining, monthly)
    return add_months(from_date, m) if m is not None else None


# ---- Reserva de emergência ----
def reserve_target(avg_monthly_expense, months):
    return (avg_monthly_expense or 0) * (months or 0)


def months_covered(current, avg_monthly_expense):
    if not avg_monthly_expense:
        return 0.0
    return (current or 0) / avg_monthly_expense


# ---- Entrada da casa ----
def house_target(property_value, down_payment_pct):
    return (property_value or 0) * (down_payment_pct or 0) / 100
