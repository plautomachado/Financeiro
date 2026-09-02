import streamlit as st

st.set_page_config(page_title="RM Money · Início", page_icon="💰",
                   layout="centered", initial_sidebar_state="collapsed")

from datetime import date
import pandas as pd

from src.components.auth import require_auth, sidebar_account
from src.components.ui import inject_css, bottom_nav
from src.services.reference_service import load_context
from src.services import dashboard_service as dash
from src.services.goal_service import list_goals, goal_progress
from src.services.currency_service import ensure_daily_rates
from src.services.transaction_service import delete_transaction
from src.utils.formatting import format_money, format_pct
from src.utils.dates import month_name, prev_month

inject_css()
require_auth()
sidebar_account()
ctx = load_context()
base = ctx["base_currency"]
ensure_daily_rates()  # atualiza câmbio 1x/dia automaticamente

st.title("Início")

# ---------- Filtros ----------
today = date.today()
c1, c2, c3 = st.columns(3)
month = c1.selectbox("Mês", list(range(1, 13)), index=today.month - 1, format_func=month_name)
year = c2.selectbox("Ano", [today.year - 1, today.year, today.year + 1], index=1)
member_opts = {"Família inteira": None}
member_opts.update({m["name"]: m["id"] for m in ctx["members"]})
member_name = c3.selectbox("Pessoa", list(member_opts.keys()))
member_id = member_opts[member_name]

s = dash.summary(year, month, member_id=member_id)
prev = s["prev"]


def _delta(cur, old):
    diff = cur - old
    if abs(diff) < 0.005:
        return None
    return format_money(diff, base)


# ---------- KPIs ----------
k1, k2, k3 = st.columns(3)
k1.metric("Receitas", format_money(s["receitas"], base), delta=_delta(s["receitas"], prev["receitas"]))
k2.metric("Despesas", format_money(s["despesas"], base),
          delta=_delta(s["despesas"], prev["despesas"]), delta_color="inverse")
k3.metric("Aportes", format_money(s["aportes"], base), delta=_delta(s["aportes"], prev["aportes"]))

k4, k5 = st.columns(2)
k4.metric("Saldo livre", format_money(s["saldo_livre"], base))
k5.metric("Taxa de economia", format_pct(s["taxa_economia"]),
          delta=_delta(s["taxa_economia"], prev["taxa_economia"]))

pm_y, pm_m = prev_month(year, month)
st.caption(f"Variação (setas) comparada a {month_name(pm_m, short=True)}/{pm_y}.")
st.divider()

txs = s["_txs"]

# ---------- Despesas por categoria ----------
st.subheader("Despesas por categoria")
cat = dash.by_category(txs, ctx["categories"])
if cat:
    df = pd.DataFrame({"Categoria": list(cat.keys()), base: list(cat.values())}).set_index("Categoria")
    st.bar_chart(df, horizontal=True)
else:
    st.info("Sem despesas lançadas neste mês ainda. Use **➕ Lançar** para começar.")

# ---------- Brasil × Japão ----------
st.subheader("Brasil × Japão")
country = dash.by_country(txs)
cc1, cc2 = st.columns(2)
cc1.metric("🇧🇷 Brasil", format_money(country.get("BR", 0), base))
cc2.metric("🇯🇵 Japão", format_money(country.get("JP", 0), base))

# ---------- Metas ----------
st.divider()
st.subheader("Metas")
goals = list_goals()
if not goals:
    st.caption("Nenhuma meta cadastrada ainda.")
for g in goals:
    p = goal_progress(g)
    icon = {"emergency": "🛟", "house": "🏠"}.get(g["type"], "🎯")
    st.write(f"{icon} **{g['name']}** — {format_money(p['current'], p['currency'])} "
             f"/ {format_money(p['target'], p['currency'])}")
    st.progress(min(p["pct"] / 100, 1.0), text=format_pct(p["pct"]))

# ---------- Últimos lançamentos (com excluir) ----------
st.divider()
st.subheader("Últimos lançamentos")
_mem = {m["id"]: m["name"] for m in ctx["members"]}
_cat = {c["id"]: f"{c.get('icon', '')} {c['name']}".strip() for c in ctx["categories"]}
_sign = {"expense": "−", "income": "+", "contribution": "→", "transfer": "↔"}
recent = txs[:15]
if not recent:
    st.caption("Nenhum lançamento neste período.")
for t in recent:
    desc = t.get("description") or _cat.get(t.get("category_id"), "—")
    dd = t["occurred_on"][8:10] + "/" + t["occurred_on"][5:7]
    row = st.columns([5, 1])
    row[0].markdown(
        f"{_sign.get(t['type'], '')}{format_money(t['amount_original'], t['currency_original'])} "
        f"· {desc} · {_mem.get(t['member_id'], '—')} · {dd}"
    )
    with row[1].popover("🗑"):
        st.caption("Excluir este lançamento?")
        if st.button("Confirmar exclusão", key=f"del_{t['id']}", type="primary"):
            delete_transaction(t["id"])
            st.rerun()

st.page_link("pages/1_Lancar.py", label="➕ Novo lançamento", use_container_width=True)

bottom_nav("inicio")
