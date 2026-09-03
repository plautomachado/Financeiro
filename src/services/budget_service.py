"""Orçamento mensal por PAÍS: planejado × realizado, projeção e status.

- Visão de UM país  -> tudo na moeda nativa (Brasil em R$, Japão em ¥).
- Visão "Todos"     -> tudo convertido para a moeda principal (base) da família.
"""
from datetime import date

from src.db.client import get_client
from src.services.reference_service import load_context, latest_rate
from src.services.transaction_service import list_transactions
from src.utils.calculations import budget_usage, budget_projection, budget_status_label
from src.utils.dates import days_in_month

# moeda nativa de cada país
COUNTRY_CCY = {"BR": "BRL", "JP": "JPY", "EU": "EUR", "US": "USD"}


def _client():
    return get_client()


def _num(x):
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def list_budgets(year, month, country=None):
    q = (_client().table("monthly_budgets").select("*")
         .eq("year", year).eq("month", month))
    if country:
        q = q.eq("country", country)
    return q.execute().data


def upsert_budget(year, month, category_id, planned_amount, currency=None, country="BR"):
    ctx = load_context()
    currency = currency or COUNTRY_CCY.get(country, ctx["base_currency"])
    existing = (_client().table("monthly_budgets").select("id")
                .eq("year", year).eq("month", month)
                .eq("category_id", category_id).eq("country", country).execute().data)
    payload = {"planned_amount": float(planned_amount), "currency": currency}
    if existing:
        return (_client().table("monthly_budgets").update(payload)
                .eq("id", existing[0]["id"]).execute())
    payload.update({
        "household_id": ctx["household_id"], "year": year, "month": month,
        "category_id": category_id, "country": country,
    })
    return _client().table("monthly_budgets").insert(payload).execute()


def delete_budget(budget_id):
    return _client().table("monthly_budgets").delete().eq("id", budget_id).execute()


def budget_status(year, month, country=None):
    """Por (categoria, país) orçado: planejado, gasto, disponível, uso%, projeção, status.

    country=None -> visão "Todos" (converte tudo para a moeda base).
    """
    ctx = load_context()
    base = ctx["base_currency"]
    cats = {c["id"]: c for c in ctx["categories"]}
    budgets = list_budgets(year, month, country)
    txs = list_transactions(year=year, month=month, type="expense")

    # gasto por (categoria, país): em moeda nativa (amount_original) e em base (amount_base)
    spent_native, spent_base = {}, {}
    for t in txs:
        key = (t["category_id"], t.get("country"))
        spent_native[key] = spent_native.get(key, 0) + _num(t.get("amount_original"))
        spent_base[key] = spent_base.get(key, 0) + _num(t.get("amount_base"))

    today = date.today()
    total_days = days_in_month(year, month)
    day = today.day if (today.year == year and today.month == month) else total_days

    rows = []
    for b in budgets:
        cid = b["category_id"]
        ctry = b.get("country", "BR")
        cur = b.get("currency") or COUNTRY_CCY.get(ctry, base)
        cat = cats.get(cid, {})
        if country:                         # visão de um país -> moeda nativa
            planned = _num(b["planned_amount"])
            gasto = spent_native.get((cid, ctry), 0)
            disp_cur = cur
        else:                               # visão "Todos" -> converte para base
            rate = 1.0 if cur == base else (latest_rate(cur, base) or 1.0)
            planned = _num(b["planned_amount"]) * rate
            gasto = spent_base.get((cid, ctry), 0)
            disp_cur = base
        usage = budget_usage(gasto, planned)
        rows.append({
            "id": b["id"], "category_id": cid, "country": ctry, "currency": disp_cur,
            "category": cat.get("name", "—"), "icon": cat.get("icon", ""),
            "planned": planned, "spent": gasto, "available": planned - gasto,
            "usage": usage, "projection": budget_projection(gasto, day, total_days),
            "status": budget_status_label(usage),
        })
    rows.sort(key=lambda r: r["usage"], reverse=True)
    return rows
