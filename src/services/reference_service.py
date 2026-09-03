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


def create_my_household(family_name, base_currency="BRL", member_name="Eu"):
    """Cria uma NOVA família isolada para o usuário logado (via função no banco)."""
    res = _client().rpc("create_household", {
        "family_name": family_name, "base_currency": base_currency, "member_name": member_name,
    }).execute()
    st.session_state.pop("context", None)
    return res.data


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


def create_category(name, kind="expense", icon=None):
    ctx = load_context()
    allcats = list_categories(active_only=False)
    order = max([c.get("sort_order", 0) for c in allcats], default=0) + 1
    return _client().table("categories").insert({
        "household_id": ctx["household_id"], "name": name, "kind": kind,
        "icon": icon, "sort_order": order, "is_active": True,
    }).execute()


def deactivate_category(category_id):
    return _client().table("categories").update({"is_active": False}).eq("id", category_id).execute()


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
