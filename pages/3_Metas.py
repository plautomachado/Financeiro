import streamlit as st

st.set_page_config(page_title="Metas", page_icon="🎯",
                   layout="centered", initial_sidebar_state="collapsed")

from src.components.auth import require_auth, sidebar_account
from src.components.ui import inject_css, bottom_nav
from src.services.reference_service import load_context
from src.services.goal_service import list_goals, goal_progress, add_contribution, simulate
from src.utils.formatting import format_money, format_pct
from src.utils.dates import month_label

inject_css()
require_auth()
sidebar_account()
ctx = load_context()

st.title("🎯 Metas")

goals = list_goals()
if not goals:
    st.info("Nenhuma meta cadastrada.")

for g in goals:
    p = goal_progress(g)
    cur = p["currency"]
    icon = {"emergency": "🛟", "house": "🏠"}.get(g["type"], "🎯")

    st.subheader(f"{icon} {g['name']}")
    st.progress(min(p["pct"] / 100, 1.0), text=format_pct(p["pct"]))

    a, b, c = st.columns(3)
    a.metric("Acumulado", format_money(p["current"], cur))
    b.metric("Meta", format_money(p["target"], cur))
    c.metric("Falta", format_money(p["remaining"], cur))

    if "months_covered" in p:
        st.caption(f"🛟 Cobre **{p['months_covered']:.1f} meses** de despesas da família.")
    if p.get("estimated_date"):
        st.caption(f"No ritmo de {format_money(p['monthly_plan'], cur)}/mês → conclusão estimada em "
                   f"**{month_label(p['estimated_date'].year, p['estimated_date'].month)}**.")
    if p.get("monthly_needed") and g.get("target_date"):
        st.caption(f"Para bater a data desejada: aporte de **{format_money(p['monthly_needed'], cur)}/mês**.")

    plan = p["monthly_plan"] or 3000
    sim_values = [round(plan), round(plan * 1.5), round(plan * 2)]
    with st.expander("📈 Simular aportes"):
        for s in simulate(g, sim_values):
            when = month_label(s["date"].year, s["date"].month) if s["date"] else "—"
            st.write(f"{format_money(s['monthly'], cur)}/mês → **{when}**")

    with st.expander("➕ Registrar aporte"):
        amt = st.number_input("Valor do aporte", min_value=0.0, step=100.0, key=f"apt_{g['id']}")
        who = st.selectbox("Por quem", ctx["members"], format_func=lambda m: m["name"], key=f"aptm_{g['id']}")
        if st.button("Aportar", key=f"aptb_{g['id']}", type="primary"):
            if amt > 0:
                add_contribution(g, amt, who["id"], currency=cur)
                st.success("Aporte registrado!")
                st.rerun()
            else:
                st.warning("Informe um valor.")

    st.divider()

bottom_nav("metas")
