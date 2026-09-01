"""Dados de referência (família, categorias, contas, câmbio) + contexto de sessão."""
import streamlit as st

from src.db.client import get_client


def _client():
    return get_client()


def get_profile():
    res = _client().table("profiles").select("*").limit(1).execute()
    return res.data[0] if res.data else None


def get_household():
    res = _client().table("households").select("*").limit(1).execute()
    return res.data[0] if res.data else None


def list_members(active_only=True):
    q = _client().table("family_members").select("*").order("sort_order")
    if active_only:
        q = q.eq("is_active", True)
    return q.execute().data


def list_categories(kind=None, active_only=True):
    q = _client().table("categories").select("*").order("sort_order")
    if active_only:
        q = q.eq("is_active", True)
    if kind:
        q = q.in_("kind", [kind, "both"])
    return q.execute().data


def list_accounts(active_only=True):
    q = _client().table("accounts").select("*").order("name")
    if active_only:
        q = q.eq("is_active", True)
    return q.execute().data


def latest_rate(from_currency, to_currency):
    if from_currency == to_currency:
        return 1.0
    res = (_client().table("exchange_rates").select("rate")
           .eq("from_currency", from_currency).eq("to_currency", to_currency)
           .order("rate_date", desc=True).limit(1).execute())
    return float(res.data[0]["rate"]) if res.data else None


def load_context():
    """Carrega e cacheia os dados de referência na sessão."""
    if "context" not in st.session_state:
        household = get_household()
        st.session_state.context = {
            "household": household,
            "household_id": household["id"] if household else None,
            "base_currency": household["base_currency"] if household else "BRL",
            "members": list_members(),
            "categories": list_categories(),
            "accounts": list_accounts(),
        }
    return st.session_state.context


def refresh_context():
    st.session_state.pop("context", None)
    return load_context()
