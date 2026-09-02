"""Tela de login + guarda de autenticação para as páginas."""
import streamlit as st

from src.services.auth_service import (
    is_authenticated, sign_in, sign_out, current_user, restore_session,
)
from src.services.reference_service import load_context


def render_login():
    st.markdown("## 💰 RM Money")
    st.caption("Finanças da família — entre para continuar.")
    with st.form("login_form"):
        email = st.text_input("E-mail")
        password = st.text_input("Senha", type="password")
        ok = st.form_submit_button("Entrar", type="primary", use_container_width=True)
    if ok:
        try:
            sign_in(email, password)
            st.rerun()
        except Exception:
            st.error("Não foi possível entrar. Confira e-mail e senha.")


def sidebar_account():
    user = current_user()
    with st.sidebar:
        if user:
            st.caption(f"👤 {getattr(user, 'email', '')}")
            if st.button("Sair", use_container_width=True):
                sign_out()
                st.rerun()


def account_section():
    """Bloco de conta (e-mail + Sair) para usar dentro de uma página."""
    user = current_user()
    if not user:
        return
    c = st.columns([3, 1])
    c[0].caption(f"👤 {getattr(user, 'email', '')}")
    if c[1].button("Sair", use_container_width=True):
        sign_out()
        st.rerun()


def require_auth():
    """Garante login + vínculo com a família. Chame no topo de cada página."""
    if not is_authenticated():
        restore_session()          # tenta relogar pelo cookie salvo
    if not is_authenticated():
        render_login()
        st.stop()
    ctx = load_context()
    if not ctx.get("household_id"):
        sidebar_account()
        st.warning(
            "Seu login ainda não está vinculado a uma família. "
            "Rode o bloco de vínculo (insert into profiles…) no SQL Editor do Supabase."
        )
        st.stop()
