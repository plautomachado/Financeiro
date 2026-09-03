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


def flush_pending_cookie():
    """Grava o cookie pendente numa execução que RENDERIZA (não descartada por rerun).

    Chamado no topo das páginas (require_auth), depois que o login já passou.
    """
    pend = st.session_state.get("_pending_cookie")
    if not pend:
        return
    ck = _cookies()
    if not ck:
        return
    try:
        ck.set(_COOKIE, json.dumps(pend), max_age=_MAX_AGE)
        st.session_state.pop("_pending_cookie", None)
    except Exception:
        pass


def sign_in(email, password):
    client = get_client()
    res = client.auth.sign_in_with_password({"email": email.strip(), "password": password})
    if res.session:
        client.postgrest.auth(res.session.access_token)
        # grava o cookie só na PRÓXIMA execução (que renderiza): se gravar aqui,
        # o st.rerun() logo em seguida descarta o "set" e o cookie se perde.
        st.session_state["_pending_cookie"] = {
            "at": res.session.access_token, "rt": res.session.refresh_token,
        }
    st.session_state.user = res.user
    st.session_state.pop("context", None)   # recarrega o contexto da família
    st.session_state.pop("_cookie_retry", None)
    return res


def restore_session():
    """Tenta relogar a partir do cookie salvo. Retorna True se conseguiu.

    A lib de cookie cacheia um {} vazio na 1ª execução da sessão e não relê
    sozinha: por isso refresh() força reler o cookie real do navegador, e damos
    UMA chance de recarregar (a hidratação do componente leva um ciclo) antes de
    concluir que o login é mesmo necessário.
    """
    if is_authenticated():
        return True
    ck = _cookies()
    if not ck:
        return False
    try:
        ck.refresh()   # ignora o cache vazio e relê os cookies reais
    except Exception:
        pass
    raw = None
    try:
        raw = ck.get(_COOKIE)
    except Exception:
        raw = None
    if not raw:
        # o componente pode não ter hidratado ainda: recarrega UMA vez e só então
        # deixa a página mostrar o login (evita pedir senha à toa).
        if not st.session_state.get("_cookie_retry"):
            st.session_state["_cookie_retry"] = True
            import time
            time.sleep(0.35)
            st.rerun()
        return False
    try:
        data = raw if isinstance(raw, dict) else json.loads(raw)
        client = get_client()
        res = client.auth.set_session(data["at"], data["rt"])
        if res and res.session:
            client.postgrest.auth(res.session.access_token)
            st.session_state.user = res.user
            st.session_state.pop("_cookie_retry", None)
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
    for k in ("sb_client", "user", "context", "_pending_cookie", "_cookie_retry"):
        st.session_state.pop(k, None)


def change_password(new_password):
    """Altera a senha do usuário logado."""
    return get_client().auth.update_user({"password": new_password})
