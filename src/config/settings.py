"""Carrega as credenciais do Supabase.

Funciona nos dois mundos:
- Streamlit Cloud / local  -> lê de st.secrets (secrets.toml)
- Render / Cloud Run / VPS -> lê de variáveis de ambiente
"""
import os

import streamlit as st


def _get(key):
    # 1) Streamlit secrets (Cloud ou secrets.toml local)
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    # 2) variável de ambiente (Render, Cloud Run, etc.)
    return os.environ.get(key)


def supabase_url():
    return _get("SUPABASE_URL")


def supabase_anon_key():
    return _get("SUPABASE_ANON_KEY")
