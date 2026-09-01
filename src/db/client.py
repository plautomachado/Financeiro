"""Cliente Supabase por sessão do usuário — para o RLS valer por login."""
import streamlit as st
from supabase import create_client, Client

from src.config.settings import supabase_url, supabase_anon_key


def get_client() -> Client:
    if "sb_client" not in st.session_state:
        url, key = supabase_url(), supabase_anon_key()
        if not url or not key:
            st.error(
                "Faltam SUPABASE_URL / SUPABASE_ANON_KEY. "
                "Preencha em .streamlit/secrets.toml (veja o secrets.toml.example)."
            )
            st.stop()
        st.session_state.sb_client = create_client(url, key)
    return st.session_state.sb_client
