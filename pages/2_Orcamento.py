import streamlit as st

st.set_page_config(page_title="Orçamento", page_icon="📊",
                   layout="centered", initial_sidebar_state="collapsed")

from datetime import date

from src.components.auth import require_auth, sidebar_account
from src.components.ui import inject_css, bottom_nav
from src.services.reference_service import load_context
from src.services.budget_service import budget_status, upsert_budget, delete_budget
from src.utils.formatting import format_money, format_pct
from src.utils.dates import month_name

inject_css()
require_auth()
sidebar_account()
ctx = load_context()
base = ctx["base_currency"]

st.title("📊 Orçamento")

today = date.today()
c1, c2 = st.columns(2)
month = c1.selectbox("Mês", list(range(1, 13)), index=today.month - 1, format_func=month_name)
year = c2.selectbox("Ano", [today.year - 1, today.year, today.year + 1], index=1)

STATUS = {"ok": ("🟢", "Normal"), "warn": ("🟡", "Atenção"), "over": ("🔴", "Acima do orçamento")}

rows = budget_status(year, month)
if not rows:
    st.info("Nenhum orçamento definido para este mês. Use **➕ Definir orçamento** abaixo.")

for r in rows:
    emoji, label = STATUS[r["status"]]
    head = st.columns([6, 1])
    head[0].markdown(f"**{r['icon']} {r['category']}** — "
                     f"{format_money(r['spent'], base)} / {format_money(r['planned'], base)} &nbsp; {emoji} {label}")
    with head[1].popover("🗑"):
        st.caption("Excluir este orçamento?")
        if st.button("Confirmar", key=f"delb_{r['id']}", type="primary"):
            delete_budget(r["id"])
            st.rerun()
    st.progress(
        min(r["usage"] / 100, 1.0),
        text=(f"{format_pct(r['usage'])} usado · disponível {format_money(r['available'], base)} · "
              f"projeção de fechamento {format_money(r['projection'], base)}"),
    )

st.divider()
with st.expander("➕ Definir / editar orçamento"):
    cats = [c for c in ctx["categories"] if c["kind"] in ("expense", "both")]
    csel = st.selectbox("Categoria", cats, format_func=lambda c: f"{c.get('icon', '')} {c['name']}".strip())
    val = st.number_input(f"Planejado para o mês ({base})", min_value=0.0, step=100.0)
    if st.button("Salvar orçamento", type="primary"):
        upsert_budget(year, month, csel["id"], val, base)
        st.success("Orçamento salvo.")
        st.rerun()

bottom_nav("orcamento")
