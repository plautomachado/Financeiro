import streamlit as st

st.set_page_config(page_title="Relatório", page_icon="📄",
                   layout="centered", initial_sidebar_state="collapsed")

from datetime import date
import pandas as pd

from src.components.auth import require_auth, sidebar_account
from src.components.ui import inject_css, bottom_nav
from src.services.reference_service import load_context
from src.services import report_service
from src.utils.formatting import format_money, format_pct
from src.utils.dates import month_name, prev_month

inject_css()
require_auth()
sidebar_account()
ctx = load_context()
base = ctx["base_currency"]

st.title("📄 Relatório mensal")

today = date.today()
c1, c2 = st.columns(2)
month = c1.selectbox("Mês", list(range(1, 13)), index=today.month - 1, format_func=month_name)
year = c2.selectbox("Ano", [today.year - 1, today.year, today.year + 1], index=1)

# país define a MOEDA do relatório (um país = moeda nativa; "Todos" = R$)
COUNTRY_FLAG = {"BR": "🇧🇷 Brasil", "JP": "🇯🇵 Japão", "EU": "🇪🇺 Europa", "US": "🇺🇸 EUA"}
fam_countries = sorted({m["default_country"] for m in ctx["members"]})
sel_country = None
if len(fam_countries) > 1:
    opts = ["🌏 Todos"] + [COUNTRY_FLAG.get(c, c) for c in fam_countries]
    pick = st.segmented_control("País", opts, default="🌏 Todos", key="rep_country") or "🌏 Todos"
    sel_country = None if pick == "🌏 Todos" else next(c for c in fam_countries if COUNTRY_FLAG.get(c, c) == pick)

rep = report_service.build(year, month, sel_country)
s = rep["summary"]
prev = rep["prev"]
cur = rep["currency"]

st.subheader(f"Fechamento de {month_name(month)}/{year}")

# ---------- Insights ----------
if rep["insights"]:
    st.markdown("##### 💡 Destaques do mês")
    for emoji, txt in rep["insights"]:
        st.markdown(f'<div class="insight"><span class="ie">{emoji}</span><span>{txt}</span></div>',
                    unsafe_allow_html=True)
else:
    st.info("Sem lançamentos suficientes neste mês para gerar destaques.")

st.divider()

# ---------- Resumo (KPIs) ----------
def _kpi(label, value, hero=False):
    cls = "kpi kpi-hero" if hero else "kpi"
    return f'<div class="{cls}"><div class="kpi-l">{label}</div><div class="kpi-v">{value}</div></div>'


st.markdown(
    '<div class="kpi-grid">'
    + _kpi("Receitas", format_money(s["receitas"], cur))
    + _kpi("Despesas", format_money(s["despesas"], cur))
    + _kpi("Aportes", format_money(s["aportes"], cur))
    + _kpi("Saldo livre", format_money(s["saldo_livre"], cur))
    + _kpi("Taxa de economia", format_pct(s["taxa_economia"]), hero=True)
    + '</div>',
    unsafe_allow_html=True,
)
pm_y, pm_m = prev_month(year, month)
st.caption(f"Mês anterior ({month_name(pm_m, short=True)}/{pm_y}): despesas {format_money(prev['despesas'], cur)} "
           f"· economia {format_pct(prev['taxa_economia'])}")

st.divider()

# ---------- Principais categorias ----------
st.subheader(f"Principais categorias ({cur})")
cat = rep["by_category"]
if cat:
    top = dict(list(cat.items())[:6])
    df = pd.DataFrame({"Categoria": list(top.keys()), cur: list(top.values())}).set_index("Categoria")
    st.bar_chart(df, horizontal=True)
else:
    st.caption("Sem despesas neste mês.")

# ---------- Por pessoa ----------
st.subheader("Por pessoa")
mem = rep["by_member"]
if mem:
    cols = st.columns(len(mem))
    for i, (name, val) in enumerate(mem.items()):
        cols[i].metric(name, format_money(val, cur))
else:
    st.caption("—")

# ---------- Brasil × Japão (só na visão "Todos", em R$) ----------
if sel_country is None and len(fam_countries) > 1:
    st.subheader("Brasil × Japão")
    ctry = rep["by_country"]
    cc = st.columns(2)
    cc[0].metric("🇧🇷 Brasil", format_money(ctry.get("BR", 0), base))
    cc[1].metric("🇯🇵 Japão", format_money(ctry.get("JP", 0), base))

st.divider()

# ---------- Orçamento planejado × realizado ----------
st.subheader("Orçamento planejado × realizado")
budgets = rep["budgets"]
if budgets:
    for b in budgets:
        st.markdown(f"**{b['icon']} {b['category']}** — {format_money(b['spent'], b['currency'])} "
                    f"/ {format_money(b['planned'], b['currency'])} ({format_pct(b['usage'], 0)})")
        st.progress(min(b["usage"] / 100, 1.0))
else:
    st.caption("Nenhum orçamento definido neste mês.")

st.divider()

# ---------- Metas ----------
st.subheader("Metas")
if rep["goals"]:
    for g, p in rep["goals"]:
        icon = {"emergency": "🛟", "house": "🏠"}.get(g["type"], "🎯")
        st.markdown(f"{icon} **{g['name']}** — {format_pct(p['pct'], 0)} · "
                    f"{format_money(p['current'], p['currency'])} / {format_money(p['target'], p['currency'])}")
        st.progress(min(p["pct"] / 100, 1.0))
else:
    st.caption("Nenhuma meta cadastrada.")

st.caption("💾 Dica: tire um print pra guardar ou compartilhar o fechamento do mês.")

bottom_nav("mais")
