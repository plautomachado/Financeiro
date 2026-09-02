import streamlit as st

st.set_page_config(page_title="Patrimônio", page_icon="🏦",
                   layout="centered", initial_sidebar_state="collapsed")

from datetime import date
import pandas as pd

from src.components.auth import require_auth, sidebar_account
from src.components.ui import inject_css, bottom_nav
from src.services.reference_service import load_context
from src.services.asset_service import (
    list_assets, create_asset, update_asset_value, deactivate_asset,
    net_worth, save_snapshot, list_snapshots, to_base, TYPE_LABELS, TYPE_ORDER,
)
from src.utils.formatting import format_money
from src.utils.dates import month_name

inject_css()
require_auth()
sidebar_account()
ctx = load_context()
base = ctx["base_currency"]
COUNTRY = {"BR": "🇧🇷 Brasil", "JP": "🇯🇵 Japão", "EU": "🇪🇺 Europa", "US": "🇺🇸 EUA"}

st.title("🏦 Patrimônio")

nw = net_worth()

# ---------- Total consolidado ----------
st.markdown(
    f'<div class="kpi-grid"><div class="kpi kpi-hero"><div class="kpi-l">Patrimônio total</div>'
    f'<div class="kpi-v">{format_money(nw["total"], base)}</div></div></div>',
    unsafe_allow_html=True,
)
b = st.columns(2)
b[0].metric("🇧🇷 Brasil", format_money(nw["by_country"].get("BR", 0), base))
b[1].metric("🇯🇵 Japão", format_money(nw["by_country"].get("JP", 0), base))

# ---------- Por tipo ----------
st.subheader("Por finalidade")
tb = nw["by_type"]
if nw["total"] > 0:
    for t in TYPE_ORDER:
        val = tb.get(t, 0)
        if val > 0:
            st.markdown(f"**{TYPE_LABELS[t]}** — {format_money(val, base)}")
            st.progress(min(val / nw["total"], 1.0))
else:
    st.caption("Cadastre seus ativos abaixo para ver o patrimônio.")

st.divider()

# ---------- Evolução ----------
st.subheader("Evolução do patrimônio")
snaps = list_snapshots()
if snaps:
    df = pd.DataFrame([
        {"Mês": f"{month_name(sn['month'], short=True)}/{str(sn['year'])[2:]}",
         base: float(sn["net_worth_base"])}
        for sn in snaps
    ]).set_index("Mês")
    st.line_chart(df)
else:
    st.caption("Salve a “foto” deste mês para começar o histórico.")

today = date.today()
if st.button(f"📸 Salvar foto de {month_name(today.month, short=True)}/{today.year}", use_container_width=True):
    save_snapshot(today.year, today.month)
    st.success("Foto do patrimônio salva!")
    st.rerun()

st.divider()

# ---------- Ativos ----------
st.subheader("Meus ativos")
for a in nw["assets"]:
    with st.container(border=True):
        r = st.columns([3, 2])
        r[0].markdown(f"**{a['name']}**")
        r[0].caption(f"{TYPE_LABELS.get(a['type'], a['type'])} · {COUNTRY.get(a['country'], a['country'])} · {a['currency']}")
        r[1].markdown(f"**{format_money(a['current_value'], a['currency'])}**")
        if a["currency"] != base:
            r[1].caption(f"≈ {format_money(to_base(a['current_value'], a['currency'], base), base)}")
        with st.expander("Editar / excluir"):
            nv = st.number_input("Valor atual", value=float(a["current_value"]), min_value=0.0,
                                 step=100.0, key=f"av_{a['id']}")
            e = st.columns(2)
            if e[0].button("Salvar valor", key=f"as_{a['id']}", type="primary"):
                update_asset_value(a["id"], nv)
                st.rerun()
            if e[1].button("Excluir ativo", key=f"ad_{a['id']}"):
                deactivate_asset(a["id"])
                st.rerun()

if not nw["assets"]:
    st.caption("Nenhum ativo cadastrado ainda.")

# ---------- Novo ativo ----------
with st.expander("➕ Novo ativo"):
    name = st.text_input("Nome", placeholder="Ex.: Conta Nubank, Poupança, Ações, Rakuten Bank", key="an")
    t1, t2 = st.columns(2)
    atype = t1.selectbox("Finalidade", TYPE_ORDER, format_func=lambda t: TYPE_LABELS[t], key="at")
    country = t2.selectbox("País", ["BR", "JP", "EU", "US"], format_func=lambda c: COUNTRY[c], key="ac")
    t3, t4 = st.columns([1, 2])
    currency = t3.selectbox("Moeda", ["BRL", "JPY", "EUR", "USD"], key="acur")
    value = t4.number_input("Valor atual", min_value=0.0, step=100.0, key="avv")
    if st.button("Salvar ativo", type="primary", key="asave"):
        if name.strip():
            create_asset(name=name.strip(), type=atype, country=country, currency=currency, current_value=value)
            st.success("Ativo cadastrado!")
            st.rerun()
        else:
            st.warning("Informe o nome do ativo.")

bottom_nav("mais")
