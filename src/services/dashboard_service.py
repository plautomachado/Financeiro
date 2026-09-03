"""Agregações do dashboard (KPIs e recortes)."""
from src.services.transaction_service import list_transactions
from src.utils.calculations import savings_rate, free_balance
from src.utils.dates import prev_month


def _num(x):
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def _agg(txs, native=False):
    """native=True soma na moeda ORIGINAL (¥, R$...); senão na moeda base (R$)."""
    f = "amount_original" if native else "amount_base"
    receitas = sum(_num(t[f]) for t in txs if t["type"] == "income")
    despesas = sum(_num(t[f]) for t in txs if t["type"] == "expense")
    aportes = sum(_num(t[f]) for t in txs if t["type"] == "contribution")
    return {
        "receitas": receitas,
        "despesas": despesas,
        "aportes": aportes,
        "saldo_livre": free_balance(receitas, despesas, aportes),
        "taxa_economia": savings_rate(receitas, despesas),
        "count": len(txs),
    }


def summary(year, month, member_id=None, country=None, native=False):
    txs = list_transactions(year=year, month=month, member_id=member_id, country=country)
    cur = _agg(txs, native)
    py, pm = prev_month(year, month)
    cur["prev"] = _agg(list_transactions(year=py, month=pm, member_id=member_id, country=country), native)
    cur["_txs"] = txs
    return cur


def by_category(txs, categories, native=False):
    f = "amount_original" if native else "amount_base"
    names = {c["id"]: f"{c.get('icon', '')} {c['name']}".strip() for c in categories}
    out = {}
    for t in txs:
        if t["type"] != "expense":
            continue
        key = names.get(t["category_id"], "Outros")
        out[key] = out.get(key, 0) + _num(t[f])
    return dict(sorted(out.items(), key=lambda x: x[1], reverse=True))


def by_member(txs, members, native=False):
    f = "amount_original" if native else "amount_base"
    names = {m["id"]: m["name"] for m in members}
    out = {}
    for t in txs:
        if t["type"] != "expense":
            continue
        key = names.get(t["member_id"], "—")
        out[key] = out.get(key, 0) + _num(t[f])
    return out


def by_country(txs):
    out = {"BR": 0.0, "JP": 0.0}
    for t in txs:
        if t["type"] != "expense":
            continue
        out[t["country"]] = out.get(t["country"], 0) + _num(t["amount_base"])
    return out
