"""Autenticação via Supabase Auth + sessão persistente (cookie)."""
import json

import streamlit as st

from src.db.client import get_client

_COOKIE = "rm_session"
_MAX_AGE = 60 * 60 * 24 * 30   # 30 dias


def current_user():
    return st.session_state.get("user")


def is_authenticated():
    return current_user() is not None


def _cookies():
    """Controller de cookies (uma instância por sessão). None se indisponível."""
    if "cookie_ctl" not in st.session_state:
        try:
            from streamlit_cookies_controller import CookieController
            st.session_state.cookie_ctl = CookieController()
        except Exception:
            st.session_state.cookie_ctl = None
    return st.session_state.cookie_ctl


def _save_cookie(session):
    ck = _cookies()
    if not ck or not session:
        return
    try:
        ck.set(_COOKIE, json.dumps({"at": session.access_token, "rt": session.refresh_token}),
               max_age=_MAX_AGE)
    except Exception:
        pass


def _clear_cookie():
    ck = _cookies()
    if not ck:
        return
    try:
        ck.remove(_COOKIE)
    except Exception:
        pass


def sign_in(email, password):
    client = get_client()
    res = client.auth.sign_in_with_password({"email": email.strip(), "password": password})
    if res.session:
        client.postgrest.auth(res.session.access_token)
        _save_cookie(res.session)
    st.session_state.user = res.user
    st.session_state.pop("context", None)   # recarrega o contexto da família
    return res


def restore_session():
    """Tenta relogar a partir do cookie salvo. Retorna True se conseguiu."""
    if is_authenticated():
        return True
    ck = _cookies()
    if not ck:
        return False
    try:
        raw = ck.get(_COOKIE)
        if not raw:
            return False
        data = raw if isinstance(raw, dict) else json.loads(raw)
        client = get_client()
        res = client.auth.set_session(data["at"], data["rt"])
        if res and res.session:
            client.postgrest.auth(res.session.access_token)
            st.session_state.user = res.user
            _save_cookie(res.session)   # tokens podem ter sido renovados
            return True
    except Exception:
        _clear_cookie()
    return False


def sign_out():
    try:
        get_client().auth.sign_out()
    except Exception:
        pass
    _clear_cookie()
    for k in ("sb_client", "user", "context"):
        st.session_state.pop(k, None)
