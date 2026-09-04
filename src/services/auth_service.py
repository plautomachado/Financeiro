"""Autenticação via Supabase Auth + sessão persistente (cookie)."""
import json

import streamlit as st

from src.db.client import get_client

_COOKIE = "rm_session"
_MAX_AGE = 60 * 60 * 24 * 30   # 30 dias
# flags essenciais p/ o cookie sobreviver DENTRO do iframe do Streamlit Cloud:
# SameSite=None + Secure + Partitioned (senão o navegador bloqueia em iframe).
_COOKIE_KW = dict(max_age=_MAX_AGE, same_site="none", secure=True, partitioned=True)


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
               **_COOKIE_KW)
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
        ck.set(_COOKIE, json.dumps(pend), **_COOKIE_KW)
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


def _ctx_cookie(name):
    """Lê o cookie direto do request (server-side): instantâneo e sem a corrida do componente."""
    try:
        return st.context.cookies.get(name)
    except Exception:
        return None


def _parse_cookie(raw):
    """Cookie pode vir como dict, JSON puro ou JSON percent-encoded (js-cookie)."""
    from urllib.parse import unquote
    if isinstance(raw, dict):
        return raw
    if not raw:
        return None
    for s in (raw, unquote(raw)):
        try:
            return json.loads(s)
        except Exception:
            continue
    return None


def restore_session():
    """Relogar a partir do cookie salvo. Retorna True se conseguiu.

    Leitura PRINCIPAL via st.context.cookies (server-side, chega no request, sem
    corrida). Se vier vazio, tenta o componente como reserva.
    """
    if is_authenticated():
        return True
    raw = _ctx_cookie(_COOKIE)
    if not raw:                       # reserva: componente de cookie
        ck = _cookies()
        if ck:
            try:
                ck.refresh()
            except Exception:
                pass
            try:
                raw = ck.get(_COOKIE)
            except Exception:
                raw = None
    data = _parse_cookie(raw)
    if not data or "at" not in data:
        return False
    try:
        client = get_client()
        res = client.auth.set_session(data["at"], data["rt"])
        if res and res.session:
            client.postgrest.auth(res.session.access_token)
            st.session_state.user = res.user
            st.session_state.pop("_cookie_retry", None)
            _save_cookie(res.session)   # regrava (tokens podem ter sido renovados)
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


def login_diagnostics():
    """Diagnóstico temporário do cookie de sessão (p/ achar por que o login não persiste)."""
    parts = []
    try:
        c = dict(st.context.cookies)
        parts.append(f"servidor: {sorted(c.keys())} · rm_session={'SIM' if _COOKIE in c else 'não'}")
    except Exception as e:
        parts.append(f"servidor: ERRO {type(e).__name__}")
    try:
        ck = _cookies()
        if ck:
            try:
                ck.refresh()
            except Exception:
                pass
            allc = ck.getAll() or {}
            parts.append(f"componente: {sorted(allc.keys())} · rm_session={'SIM' if _COOKIE in allc else 'não'}")
        else:
            parts.append("componente: indisponível")
    except Exception as e:
        parts.append(f"componente: ERRO {type(e).__name__}")
    return "  ||  ".join(parts)
