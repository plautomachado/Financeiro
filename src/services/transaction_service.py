"""CRUD de transações (o núcleo do app)."""
from datetime import date

from src.db.client import get_client
from src.services.reference_service import load_context, latest_rate
from src.utils.dates import month_bounds


def _client():
    return get_client()


def create_transaction(*, type, amount_original, currency_original, country,
                       member_id, base_currency=None, exchange_rate=None,
                       category_id=None, subcategory_id=None, account_id=None,
                       goal_id=None, description=None, note=None, occurred_on=None):
    ctx = load_context()
    base_currency = base_currency or ctx["base_currency"]
    if exchange_rate is None:
        if currency_original == base_currency:
            exchange_rate = 1.0
        else:
            exchange_rate = latest_rate(currency_original, base_currency) or 1.0
    payload = {
        "household_id": ctx["household_id"],
        "member_id": member_id,
        "type": type,
        "amount_original": float(amount_original),
        "currency_original": currency_original,
        "country": country,
        "exchange_rate": float(exchange_rate),
        "base_currency": base_currency,
        "category_id": category_id,
        "subcategory_id": subcategory_id,
        "account_id": account_id,
        "goal_id": goal_id,
        "description": description,
        "note": note,
        "occurred_on": (occurred_on or date.today()).isoformat(),
    }
    res = _client().table("transactions").insert(payload).execute()
    return res.data[0] if res.data else None


def list_transactions(year=None, month=None, member_id=None, country=None,
                      type=None, limit=1000):
    q = _client().table("transactions").select("*").order("occurred_on", desc=True)
    if year and month:
        start, end = month_bounds(year, month)
        q = q.gte("occurred_on", start.isoformat()).lte("occurred_on", end.isoformat())
    if member_id:
        q = q.eq("member_id", member_id)
    if country:
        q = q.eq("country", country)
    if type:
        q = q.eq("type", type)
    return q.limit(limit).execute().data


def update_transaction(tx_id, updates):
    return _client().table("transactions").update(updates).eq("id", tx_id).execute()


def delete_transaction(tx_id):
    return _client().table("transactions").delete().eq("id", tx_id).execute()
