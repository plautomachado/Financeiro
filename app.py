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

# lança as recorrências marcadas como "débito automático" que já venceram
if st.session_state.get("_recur_check") != date.today().isoformat():
    st.session_state["_recur_check"] = date.today().isoformat()
    try:
        from src.services.recurring_service import auto_post_due
        auto_post_due()
    except Exception:
        pass

st.title("Início")

# ---------- Filtros ----------
COUNTRY_FLAG = {"BR": "🇧🇷 Brasil", "JP": "🇯🇵 Japão", "EU": "🇪🇺 Europa", "US": "🇺🇸 EUA"}
COUNTRY_CCY = {"BR": "BRL", "JP": "JPY", "EU": "EUR", "US": "USD"}
today = date.today()
c1, c2 = st.columns(2)
month = c1.selectbox("Mês", list(range(1, 13)), index=today.month - 1, format_func=month_name)
year = c2.selectbox("Ano", [today.year - 1, today.year, today.year + 1], index=1)

# país define a MOEDA da visão: um país = moeda nativa (¥, R$); "Todos" = tudo em R$
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

# ---------- Resumo no topo: gastos do mês por país, cada um na sua moeda ----------
if len(fam_countries) > 1:
    ct = dash.country_totals(year, month, member_id=member_id)
    cols = st.columns(len(fam_countries))
    for i, c in enumerate(fam_countries):
        cols[i].metric(COUNTRY_FLAG.get(c, c), format_money(ct.get(c, 0), COUNTRY_CCY.get(c, base)))
    st.caption("Gasto do mês em cada país (na moeda de lá).")

native = sel_country is not None
disp_cur = COUNTRY_CCY.get(sel_country, base) if native else base
s = dash.summary(year, month, member_id=member_id, country=sel_country, native=native)


# ---------- KPIs (grade 2 colunas, estilo mockup) ----------
def _kpi(label, value, hero=False):
    cls = "kpi kpi-hero" if hero else "kpi"
    return f'<div class="{cls}"><div class="kpi-l">{label}</div><div class="kpi-v">{value}</div></div>'


st.markdown(
    '<div class="kpi-grid">'
    + _kpi("Receitas", format_money(s["receitas"], disp_cur))
    + _kpi("Despesas", format_money(s["despesas"], disp_cur))
    + _kpi("Aportes", format_money(s["aportes"], disp_cur))
    + _kpi("Saldo livre", format_money(s["saldo_livre"], disp_cur))
    + _kpi("Taxa de economia", format_pct(s["taxa_economia"]), hero=True)
    + '</div>',
    unsafe_allow_html=True,
)
st.divider()

txs = s["_txs"]

# ---------- Despesas por categoria ----------
st.subheader(f"Despesas por categoria ({disp_cur})")
cat = dash.by_category(txs, ctx["categories"], native=native)
if cat:
    df = pd.DataFrame({"Categoria": list(cat.keys()), disp_cur: list(cat.values())}).set_index("Categoria")
    st.bar_chart(df, horizontal=True)
else:
    st.info("Sem despesas lançadas neste mês ainda. Use **➕ Lançar** para começar.")

# ---------- Brasil × Japão (só na visão "Todos", em R$) ----------
if sel_country is None and len(fam_countries) > 1:
    st.subheader("Brasil × Japão")
    country = dash.by_country(txs)
    cc1, cc2 = st.columns(2)
    cc1.metric("🇧🇷 Brasil", format_money(country.get("BR", 0), base))
    cc2.metric("🇯🇵 Japão", format_money(country.get("JP", 0), base))

# ---------- Evolução (últimos 6 meses) ----------
st.divider()
st.subheader(f"📈 Evolução — últimos 6 meses ({disp_cur})")
serie = dash.monthly_series(year, month, n=6, member_id=member_id, country=sel_country, native=native)
if any(x["despesas"] or x["receitas"] for x in serie):
    labels = [f"{month_name(x['m'], short=True)}/{str(x['y'])[2:]}" for x in serie]
    df_ev = pd.DataFrame(
        {"Receitas": [x["receitas"] for x in serie], "Despesas": [x["despesas"] for x in serie]},
        index=labels,
    )
    st.line_chart(df_ev, color=["#0E7C66", "#C2442E"])
    _dm = serie[-1]["despesas"]
    _dp = serie[-2]["despesas"] if len(serie) >= 2 else 0
    if _dp:
        _ch = (_dm - _dp) / _dp * 100
        seta = "🔺" if _ch > 0 else "🔻"
        st.caption(f"{seta} Despesas {format_pct(abs(_ch), 0)} vs. o mês anterior.")
else:
    st.caption("Sem dados suficientes ainda para o gráfico.")

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
