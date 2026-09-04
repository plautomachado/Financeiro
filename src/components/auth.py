"""Tela de login + guarda de autenticação para as páginas."""
import streamlit as st

from src.services.auth_service import (
    is_authenticated, sign_in, sign_out, current_user, restore_session, change_password,
    flush_pending_cookie, login_diagnostics,
)
from src.services.reference_service import load_context, refresh_context, create_my_household


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
        except Exception:
            st.error("Não foi possível entrar. Confira e-mail e senha.")
        else:
            st.rerun()
    with st.expander("🔎 diagnóstico (temporário)"):
        st.caption(login_diagnostics())


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
    with st.expander("🔑 Alterar minha senha"):
        p1 = st.text_input("Nova senha", type="password", key="pw_new")
        p2 = st.text_input("Repita a nova senha", type="password", key="pw_new2")
        if st.button("Salvar nova senha", type="primary", key="pw_save"):
            if len(p1) < 6:
                st.warning("A senha precisa ter pelo menos 6 caracteres.")
            elif p1 != p2:
                st.warning("As senhas não conferem.")
            else:
                try:
                    change_password(p1)
                    st.success("Senha alterada! Use a nova no próximo login. ✅")
                except Exception as e:
                    st.error(f"Não consegui alterar: {e}")


def render_onboarding():
    st.markdown("## 👋 Bem-vindo ao RM Money")
    st.caption("Vamos criar a sua família. Seus dados ficam **só seus** — ninguém mais vê.")
    with st.form("onboarding"):
        fam = st.text_input("Nome da família", placeholder="Ex.: Família Silva")
        name = st.text_input("Seu nome", placeholder="Como você aparece nos lançamentos")
        cur = st.selectbox("Moeda principal", ["BRL", "JPY", "EUR", "USD"])
        ok = st.form_submit_button("Criar minha família", type="primary", use_container_width=True)
    if ok:
        if not fam.strip():
            st.warning("Dê um nome para a sua família.")
        else:
            try:
                create_my_household(fam.strip(), cur, (name.strip() or "Eu"))
                refresh_context()
                st.success("Família criada! 🎉")
                st.rerun()
            except Exception as e:
                st.error(f"Não consegui criar a família: {e}")


def require_auth():
    """Garante login + família (mostra o onboarding se ainda não tiver). Chame no topo de cada página."""
    if not is_authenticated():
        restore_session()          # tenta relogar pelo cookie salvo
    if not is_authenticated():
        render_login()
        st.stop()
    flush_pending_cookie()     # grava o cookie de sessão numa execução que renderiza
    ctx = load_context()
    if not ctx.get("household_id"):
        render_onboarding()
        st.stop()
