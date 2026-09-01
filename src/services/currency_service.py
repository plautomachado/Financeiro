"""Câmbio automático: busca USD→BRL, EUR→BRL, JPY→BRL de uma API grátis (sem chave).

- Fonte primária: open.er-api.com ; reserva: frankfurter.dev
- Guarda no histórico `exchange_rates` (mantendo a taxa por dia).
- Respeita override manual: a atualização automática do dia só ocorre se ainda
  não houver cotação para hoje (o botão "Atualizar agora" força).
"""
import json
import urllib.request
from datetime import date

import streamlit as st

from src.db.client import get_client
from src.services.reference_service import load_context, latest_rate, refresh_context

BASE = "BRL"
FOREIGN = ["USD", "EUR", "JPY"]

_SOURCES = [
    "https://open.er-api.com/v6/latest/BRL",
    "https://api.frankfurter.dev/v1/latest?base=BRL&symbols=USD,EUR,JPY",
]


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_rates_to_brl():
    """Retorna {'USD': x, 'EUR': y, 'JPY': z} = valor de 1 unidade da moeda em R$."""
    for url in _SOURCES:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "RMMoney/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            rates = data.get("rates") or {}
            out = {}
            for cur in FOREIGN:
                per_brl = rates.get(cur)          # 1 BRL = per_brl <cur>
                if per_brl:
                    out[cur] = round(1.0 / float(per_brl), 6)   # 1 <cur> = out[cur] BRL
            if len(out) == len(FOREIGN):
                return out
        except Exception:
            continue
    return {}


def update_rates_to_brl():
    """Busca e grava JPY/USD/EUR → BRL (e o inverso) no histórico, com data de hoje."""
    ctx = load_context()
    rates = fetch_rates_to_brl()
    if not rates:
        return {}
    today = date.today().isoformat()
    rows = []
    for cur, brl in rates.items():
        rows.append({"household_id": ctx["household_id"], "from_currency": cur,
                     "to_currency": BASE, "rate": brl, "rate_date": today, "source": "auto"})
        rows.append({"household_id": ctx["household_id"], "from_currency": BASE,
                     "to_currency": cur, "rate": round(1.0 / brl, 8), "rate_date": today, "source": "auto"})
    get_client().table("exchange_rates").upsert(
        rows, on_conflict="household_id,from_currency,to_currency,rate_date"
    ).execute()
    refresh_context()
    return rates


def ensure_daily_rates():
    """Atualiza automaticamente 1x por dia (só se ainda não houver cotação de hoje)."""
    today = date.today().isoformat()
    if st.session_state.get("_rates_checked") == today:
        return
    st.session_state["_rates_checked"] = today
    try:
        existing = (get_client().table("exchange_rates").select("id")
                    .eq("from_currency", "JPY").eq("to_currency", BASE)
                    .eq("rate_date", today).limit(1).execute().data)
        if not existing:
            update_rates_to_brl()
    except Exception:
        pass


def current_rates_to_brl():
    """Últimas taxas conhecidas X→BRL (para exibição)."""
    return {cur: (latest_rate(cur, BASE) or 0) for cur in FOREIGN}
