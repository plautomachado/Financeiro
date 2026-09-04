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


def _convert(amount, from_cur, to_cur):
    """Converte entre moedas via base (ex.: € -> R$ -> ¥). Sem taxa, mantém o valor."""
    amount = _num(amount)
    if not amount or from_cur == to_cur:
        return amount
    base = load_context()["base_currency"]
    rf = 1.0 if from_cur == base else latest_rate(from_cur, base)
    rt = 1.0 if to_cur == base else latest_rate(to_cur, base)
    if not rf or not rt:
        return amount
    return amount * rf / rt


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
        if not cid:                 # linha de "teto do mês" (sem categoria) -> tratada à parte
            continue
        ctry = b.get("country", "BR")
        src_cur = b.get("currency") or COUNTRY_CCY.get(ctry, base)
        native_cur = COUNTRY_CCY.get(ctry, base)
        cat = cats.get(cid, {})
        if country:                         # visão de um país -> moeda do país (converte o valor se preciso)
            planned = _convert(b["planned_amount"], src_cur, native_cur)
            gasto = spent_native.get((cid, ctry), 0)
            disp_cur = native_cur
        else:                               # visão "Todos" -> converte para base
            planned = _convert(b["planned_amount"], src_cur, base)
            gasto = spent_base.get((cid, ctry), 0)
            disp_cur = base
        usage = budget_usage(gasto, planned)
        rows.append({
            "id": b["id"], "category_id": cid, "country": ctry, "currency": disp_cur,
            "src_amount": _num(b["planned_amount"]), "src_currency": src_cur,
            "category": cat.get("name", "—"), "icon": cat.get("icon", ""),
            "planned": planned, "spent": gasto, "available": planned - gasto,
            "usage": usage, "projection": budget_projection(gasto, day, total_days),
            "status": budget_status_label(usage),
        })
    rows.sort(key=lambda r: r["usage"], reverse=True)
    return rows


# ---------- Teto do mês (orçamento total, sem categoria) ----------
def get_total_budget(year, month, country=None):
    """Linha(s) de teto (category_id NULL). country=None -> de todos os países."""
    q = (_client().table("monthly_budgets").select("*")
         .eq("year", year).eq("month", month).is_("category_id", "null"))
    if country:
        q = q.eq("country", country)
    return q.execute().data


def upsert_total_budget(year, month, planned_amount, currency, country):
    ctx = load_context()
    existing = (_client().table("monthly_budgets").select("id")
                .eq("year", year).eq("month", month).eq("country", country)
                .is_("category_id", "null").execute().data)
    payload = {"planned_amount": float(planned_amount), "currency": currency}
    if existing:
        return (_client().table("monthly_budgets").update(payload)
                .eq("id", existing[0]["id"]).execute())
    payload.update({
        "household_id": ctx["household_id"], "year": year, "month": month,
        "category_id": None, "country": country,
    })
    return _client().table("monthly_budgets").insert(payload).execute()


def total_status(year, month, country=None):
    """Status do teto do mês. Retorna None se não houver teto definido.

    country específico -> moeda nativa; None ("Todos") -> soma tetos convertidos p/ base.
    """
    ctx = load_context()
    base = ctx["base_currency"]
    caps = get_total_budget(year, month, country)
    txs = list_transactions(year=year, month=month, type="expense", country=country)

    src_amount, src_currency = None, None
    if country:
        cur = COUNTRY_CCY.get(country, base)
        spent = sum(_num(t.get("amount_original")) for t in txs)
        if caps:
            src_amount = _num(caps[0]["planned_amount"])
            src_currency = caps[0].get("currency") or cur
            planned = _convert(src_amount, src_currency, cur)   # ex.: € -> ¥
            cap_id = caps[0]["id"]
        else:
            planned, cap_id = 0.0, None
    else:
        cur = base
        spent = sum(_num(t.get("amount_base")) for t in txs)
        planned = sum(_convert(c["planned_amount"], c.get("currency") or base, base) for c in caps)
        cap_id = None

    if planned <= 0:
        return None
    today = date.today()
    total_days = days_in_month(year, month)
    day = today.day if (today.year == year and today.month == month) else total_days
    usage = budget_usage(spent, planned)
    return {
        "id": cap_id, "currency": cur, "planned": planned, "spent": spent,
        "src_amount": src_amount, "src_currency": src_currency,
        "available": planned - spent, "usage": usage,
        "projection": budget_projection(spent, day, total_days),
        "status": budget_status_label(usage),
    }
