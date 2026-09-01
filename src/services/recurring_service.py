"""Despesas recorrentes: definições + ocorrências do mês (previsto × pago)."""
from calendar import monthrange
from datetime import date

from src.db.client import get_client
from src.services.reference_service import load_context, latest_rate
from src.services.transaction_service import create_transaction, list_transactions, delete_transaction


def _client():
    return get_client()


def list_recurring(active_only=True):
    q = _client().table("recurring_transactions").select("*").order("description")
    if active_only:
        q = q.eq("is_active", True)
    return q.execute().data


def create_recurring(*, description, amount, currency, country, member_id,
                     category_id=None, account_id=None, type="expense",
                     periodicity="monthly", due_day=1, start_date=None, end_date=None):
    ctx = load_context()
    payload = {
        "household_id": ctx["household_id"], "member_id": member_id, "type": type,
        "description": description, "amount": float(amount), "currency": currency, "country": country,
        "category_id": category_id, "account_id": account_id, "periodicity": periodicity,
        "due_day": int(due_day), "start_date": (start_date or date.today()).isoformat(),
        "end_date": end_date.isoformat() if end_date else None, "is_active": True,
    }
    return _client().table("recurring_transactions").insert(payload).execute()


def deactivate_recurring(rec_id):
    return _client().table("recurring_transactions").update({"is_active": False}).eq("id", rec_id).execute()


def occurrences_for_month(year, month):
    """Para cada recorrência ativa que incide no mês: due_date + se já foi paga."""
    defs = list_recurring(active_only=True)
    last_day = monthrange(year, month)[1]
    month_start, month_end = date(year, month, 1), date(year, month, last_day)

    txs = list_transactions(year=year, month=month, limit=2000)
    paid_by = {t["recurring_id"]: t for t in txs if t.get("recurring_id")}

    out = []
    for d in defs:
        start = date.fromisoformat(d["start_date"])
        end = date.fromisoformat(d["end_date"]) if d.get("end_date") else None
        if start > month_end or (end and end < month_start):
            continue
        if d.get("periodicity") == "yearly" and start.month != month:
            continue
        due_day = d.get("due_day") or start.day
        due = date(year, month, min(due_day, last_day))
        tx = paid_by.get(d["id"])
        out.append({"recurring": d, "due_date": due, "paid": tx is not None, "transaction": tx})
    out.sort(key=lambda o: o["due_date"])
    return out


def mark_paid(rec, year, month, occurred_on=None):
    last_day = monthrange(year, month)[1]
    due = occurred_on or date(year, month, min(rec.get("due_day") or 1, last_day))
    return create_transaction(
        type=rec["type"], amount_original=rec["amount"], currency_original=rec["currency"],
        country=rec["country"], member_id=rec["member_id"], category_id=rec.get("category_id"),
        account_id=rec.get("account_id"), description=rec["description"],
        occurred_on=due, recurring_id=rec["id"],
    )


def unmark_paid(transaction_id):
    return delete_transaction(transaction_id)


def to_base(amount, currency, base):
    if currency == base:
        return float(amount or 0)
    return float(amount or 0) * (latest_rate(currency, base) or 1)
