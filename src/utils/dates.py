"""Utilitários de data (nomes de meses em pt-BR, limites de mês, etc.)."""
from datetime import date
import calendar

MONTHS_PT = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
             "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MONTHS_PT_SHORT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                   "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def month_name(month, short=False):
    return (MONTHS_PT_SHORT if short else MONTHS_PT)[int(month) - 1]


def month_label(year, month, short=True):
    return f"{month_name(month, short)}/{year}"


def month_bounds(year, month):
    last = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last)


def days_in_month(year, month):
    return calendar.monthrange(year, month)[1]


def prev_month(year, month):
    return (year - 1, 12) if month == 1 else (year, month - 1)


def add_months(d, months):
    m = d.month - 1 + int(months)
    y = d.year + m // 12
    m = m % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return date(y, m, day)
