"""Orçamento mensal: planejado × realizado, projeção e status."""
from datetime import date

from src.db.client import get_client
from src.services.reference_service import load_context
from src.services.transaction_service import list_transactions
from src.utils.calculations import budget_usage, budget_projection, budget_status_label
from src.utils.dates import days_in_month


def _client():
    return get_client()


def _num(x):
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def list_budgets(year, month):
    return (_client().table("monthly_budgets").select("*")
            .eq("year", year).eq("month", month).execute().data)


def upsert_budget(year, month, category_id, planned_amount, currency=None):
    ctx = load_context()
    currency = currency or ctx["base_currency"]
    existing = (_client().table("monthly_budgets").select("id")
                .eq("year", year).eq("month", month)
                .eq("category_id", category_id).execute().data)
    payload = {"planned_amount": float(planned_amount), "currency": currency}
    if existing:
        return (_client().table("monthly_budgets").update(payload)
                .eq("id", existing[0]["id"]).execute())
    payload.update({
        "household_id": ctx["household_id"], "year": year,
        "month": month, "category_id": category_id,
    })
    return _client().table("monthly_budgets").insert(payload).execute()


def budget_status(year, month):
    """Retorna, por categoria orçada: planejado, gasto, disponível, uso%, projeção, status."""
    ctx = load_context()
    cats = {c["id"]: c for c in ctx["categories"]}
    budgets = list_budgets(year, month)
    txs = list_transactions(year=year, month=month, type="expense")

    spent = {}
    for t in txs:
        spent[t["category_id"]] = spent.get(t["category_id"], 0) + _num(t["amount_base"])

    today = date.today()
    total_days = days_in_month(year, month)
    day = today.day if (today.year == year and today.month == month) else total_days

    rows = []
    for b in budgets:
        cid = b["category_id"]
        planned = _num(b["planned_amount"])
        gasto = spent.get(cid, 0)
        usage = budget_usage(gasto, planned)
        cat = cats.get(cid, {})
        rows.append({
            "category_id": cid,
            "category": cat.get("name", "—"),
            "icon": cat.get("icon", ""),
            "planned": planned,
            "spent": gasto,
            "available": planned - gasto,
            "usage": usage,
            "projection": budget_projection(gasto, day, total_days),
            "status": budget_status_label(usage),
        })
    rows.sort(key=lambda r: r["usage"], reverse=True)
    return rows
