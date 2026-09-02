"""Cartões de crédito + compras parceladas (gera N lançamentos)."""
from datetime import date

from src.db.client import get_client
from src.services.reference_service import load_context
from src.services.transaction_service import create_transaction
from src.utils.dates import add_months


def _client():
    return get_client()


def list_cards(active_only=True):
    q = _client().table("credit_cards").select("*").order("name")
    if active_only:
        q = q.eq("is_active", True)
    return q.execute().data


def create_card(*, name, currency, card_limit=None, closing_day=None, due_day=None, member_id=None):
    ctx = load_context()
    return _client().table("credit_cards").insert({
        "household_id": ctx["household_id"], "name": name, "currency": currency,
        "card_limit": (float(card_limit) if card_limit else None),
        "closing_day": closing_day, "due_day": due_day, "member_id": member_id, "is_active": True,
    }).execute()


def deactivate_card(card_id):
    return _client().table("credit_cards").update({"is_active": False}).eq("id", card_id).execute()


def list_installments(limit=50):
    return (_client().table("installments").select("*")
            .order("created_at", desc=True).limit(limit).execute().data)


def create_installment(*, description, total_amount, currency, country, member_id,
                       installments_count, first_date=None, category_id=None,
                       credit_card_id=None, account_id=None):
    """Cria a compra parcelada e gera N lançamentos (1 por mês)."""
    ctx = load_context()
    first_date = first_date or date.today()
    n = int(installments_count)
    total = float(total_amount)

    inst = _client().table("installments").insert({
        "household_id": ctx["household_id"], "member_id": member_id, "description": description,
        "total_amount": total, "currency": currency, "country": country,
        "installments_count": n, "first_date": first_date.isoformat(),
        "category_id": category_id, "credit_card_id": credit_card_id, "account_id": account_id,
    }).execute().data[0]

    parcela = round(total / n, 2)
    for i in range(1, n + 1):
        amt = parcela if i < n else round(total - parcela * (n - 1), 2)   # ajuste de arredondamento na última
        create_transaction(
            type="expense", amount_original=amt, currency_original=currency, country=country,
            member_id=member_id, category_id=category_id, credit_card_id=credit_card_id,
            account_id=account_id, installment_id=inst["id"], installment_no=i,
            description=f"{description} ({i}/{n})", occurred_on=add_months(first_date, i - 1),
        )
    return inst, parcela
