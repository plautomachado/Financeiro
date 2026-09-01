"""Carrega as credenciais do Supabase pelo Streamlit."""

import streamlit as st


def supabase_url():
    return st.secrets.get("SUPABASE_URL")


def supabase_anon_key():
    return st.secrets.get("SUPABASE_ANON_KEY")