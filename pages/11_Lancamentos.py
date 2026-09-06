import streamlit as st

st.set_page_config(page_title="Lançamentos", page_icon="📋",
                   layout="centered", initial_sidebar_state="collapsed")

from datetime import date

from src.components.auth import require_auth, sidebar_account
from src.components.ui import inject_css, bottom_nav
from src.components.tx_ui import render_tx_list
from src.services.reference_service import load_context
from src.services.transaction_service import list_transactions
from src.utils.dates import month_name

inject_css()
require_auth()
sidebar_account()
ctx = load_context()
base = ctx["base_currency"]

COUNTRY_FLAG = {"BR": "🇧🇷 Brasil", "JP": "🇯🇵 Japão", "EU": "🇪🇺 Europa", "US": "🇺🇸 EUA"}

st.title("📋 Lançamentos")
st.caption("Todos os lançamentos do mês — **edite** ✏️ ou **exclua** 🗑 o que precisar.")

today = date.today()
c1, c2 = st.columns(2)
month = c1.selectbox("Mês", list(range(1, 13)), index=today.month - 1, format_func=month_name)
year = c2.selectbox("Ano", [today.year - 1, today.year, today.year + 1], index=1)

# país (adaptável)
fam_countries = sorted({m["default_country"] for m in ctx["members"]})
sel_country = None
if len(fam_countries) > 1:
    opts = ["🌏 Todos"] + [COUNTRY_FLAG.get(c, c) for c in fam_countries]
    pick = st.segmented_control("País", opts, default="🌏 Todos") or "🌏 Todos"
    sel_country = None if pick == "🌏 Todos" else next(c for c in fam_countries if COUNTRY_FLAG.get(c, c) == pick)

member_opts = {"Família inteira": None}
member_opts.update({m["name"]: m["id"] for m in ctx["members"]})
member_name = st.selectbox("Pessoa", list(member_opts.keys()))
member_id = member_opts[member_name]

txs = list_transactions(year=year, month=month, member_id=member_id, country=sel_country, limit=2000)
st.divider()
st.caption(f"**{len(txs)}** lançamento(s) em {month_name(month)}/{year}.")
render_tx_list(txs, ctx, base, key_prefix="lanc")

bottom_nav("mais")
