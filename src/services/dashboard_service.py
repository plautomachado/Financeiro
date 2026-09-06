"""Agregações do dashboard (KPIs e recortes).

Regra de moeda: cada visão tem uma moeda (`view_cur`). Todo valor é CONVERTIDO
para ela — inclusive quando a moeda original é diferente (ex.: salário em € numa
visão em ¥ vira o equivalente em ¥). Se `view_cur` é None ou = base, usa amount_base (R$).
"""
from datetime import date

from src.services.transaction_service import list_transactions
from src.services.reference_service import latest_rate, load_context
from src.utils.calculations import savings_rate, free_balance
from src.utils.dates import prev_month

COUNTRY_CCY = {"BR": "BRL", "JP": "JPY", "EU": "EUR", "US": "USD"}


def _num(x):
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def _base():
    try:
        return load_context().get("base_currency", "BRL")
    except Exception:
        return "BRL"


def _conv_fn(view_cur=None, base=None):
    """Retorna função(tx) -> valor convertido para view_cur (via moeda base)."""
    base = base or _base()
    if not view_cur or view_cur == base:
        return lambda t: _num(t.get("amount_base"))
    rate = latest_rate(view_cur, base)   # ex.: JPY->BRL

    def conv(t):
        if t.get("currency_original") == view_cur:      # já está na moeda -> exato
            return _num(t.get("amount_original"))
        ab = _num(t.get("amount_base"))                 # em base (R$)
        return (ab / rate) if rate else _num(t.get("amount_original"))

    return conv


def _agg(txs, view_cur=None, base=None):
    conv = _conv_fn(view_cur, base)
    receitas = sum(conv(t) for t in txs if t["type"] == "income")
    despesas = sum(conv(t) for t in txs if t["type"] == "expense")
    aportes = sum(conv(t) for t in txs if t["type"] == "contribution")
    return {
        "receitas": receitas,
        "despesas": despesas,
        "aportes": aportes,
        "saldo_livre": free_balance(receitas, despesas, aportes),
        "taxa_economia": savings_rate(receitas, despesas),
        "count": len(txs),
    }


def summary(year, month, member_id=None, country=None, view_cur=None, base=None):
    txs = list_transactions(year=year, month=month, member_id=member_id, country=country)
    cur = _agg(txs, view_cur, base)
    py, pm = prev_month(year, month)
    cur["prev"] = _agg(list_transactions(year=py, month=pm, member_id=member_id, country=country), view_cur, base)
    cur["_txs"] = txs
    return cur


def by_category(txs, categories, view_cur=None, base=None):
    conv = _conv_fn(view_cur, base)
    names = {c["id"]: f"{c.get('icon', '')} {c['name']}".strip() for c in categories}
    out = {}
    for t in txs:
        if t["type"] != "expense":
            continue
        key = names.get(t["category_id"], "Outros")
        out[key] = out.get(key, 0) + conv(t)
    return dict(sorted(out.items(), key=lambda x: x[1], reverse=True))


def by_member(txs, members, view_cur=None, base=None):
    conv = _conv_fn(view_cur, base)
    names = {m["id"]: m["name"] for m in members}
    out = {}
    for t in txs:
        if t["type"] != "expense":
            continue
        key = names.get(t["member_id"], "—")
        out[key] = out.get(key, 0) + conv(t)
    return out


def by_country(txs):
    """Despesa por país na moeda BASE (R$) — usado na comparação da visão 'Todos'."""
    out = {"BR": 0.0, "JP": 0.0}
    for t in txs:
        if t["type"] != "expense":
            continue
        out[t["country"]] = out.get(t["country"], 0) + _num(t["amount_base"])
    return out


def country_totals(year, month, member_id=None, base=None):
    """Gastos do mês por país, cada um convertido para a MOEDA NATIVA daquele país."""
    base = base or _base()
    txs = list_transactions(year=year, month=month, member_id=member_id, type="expense")
    convs, out = {}, {}
    for t in txs:
        ctry = t.get("country")
        vc = COUNTRY_CCY.get(ctry, base)
        if vc not in convs:
            convs[vc] = _conv_fn(vc, base)
        out[ctry] = out.get(ctry, 0) + convs[vc](t)
    return out


def category_averages(n_months=6, member_id=None, country=None, view_cur=None, base=None, ref=None):
    """Média MENSAL de despesa por categoria + total, nos últimos n_months.

    Divide pelo nº de meses que TÊM lançamento (com 2 meses de dados, divide por 2).
    """
    conv = _conv_fn(view_cur, base)
    ref = ref or date.today()
    months = []
    y, m = ref.year, ref.month
    for _ in range(n_months):
        months.append((y, m))
        y, m = prev_month(y, m)

    per_cat, total, months_with_data = {}, 0.0, 0
    for (yr, mo) in months:
        txs = list_transactions(year=yr, month=mo, member_id=member_id, country=country, type="expense")
        month_sum = 0.0
        for t in txs:
            v = conv(t)
            per_cat[t.get("category_id")] = per_cat.get(t.get("category_id"), 0) + v
            month_sum += v
        if month_sum > 0:
            months_with_data += 1
        total += month_sum

    div = max(months_with_data, 1)
    return {
        "per_cat_avg": {cid: v / div for cid, v in per_cat.items()},
        "total_avg": total / div,
        "months": months_with_data,
    }
