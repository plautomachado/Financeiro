"""Autenticação via Supabase Auth."""
import streamlit as st

from src.db.client import get_client


def current_user():
    return st.session_state.get("user")


def is_authenticated():
    return current_user() is not None


def sign_in(email, password):
    client = get_client()
    res = client.auth.sign_in_with_password({"email": email.strip(), "password": password})
    if res.session:
        # garante que as consultas ao banco usem o JWT do usuário (RLS)
        client.postgrest.auth(res.session.access_token)
    st.session_state.user = res.user
    st.session_state.pop("context", None)  # força recarregar o contexto da família
    return res


def sign_out():
    try:
        get_client().auth.sign_out()
    except Exception:
        pass
    for k in ("sb_client", "user", "context"):
        st.session_state.pop(k, None)
