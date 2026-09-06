import streamlit as st

st.set_page_config(page_title="Médias", page_icon="📊",
                   layout="centered", initial_sidebar_state="collapsed")

import pandas as pd

from src.components.auth import require_auth, sidebar_account
from src.components.ui import inject_css, bottom_nav
from src.services.reference_service import load_context
from src.services import dashboard_service as dash
from src.utils.formatting import format_money

inject_css()
require_auth()
sidebar_account()
ctx = load_context()
base = ctx["base_currency"]

COUNTRY_FLAG = {"BR": "🇧🇷 Brasil", "JP": "🇯🇵 Japão", "EU": "🇪🇺 Europa", "US": "🇺🇸 EUA"}
COUNTRY_CCY = {"BR": "BRL", "JP": "JPY", "EU": "EUR", "US": "USD"}

st.title("📊 Médias mensais")
st.caption("Quanto você gasta, **em média, por mês** — em cada categoria e no total. Uma referência do padrão de gastos.")

# país define a moeda (adaptável)
fam_countries = sorted({m["default_country"] for m in ctx["members"]})
sel_country = None
if len(fam_countries) > 1:
    opts = ["🌏 Todos"] + [COUNTRY_FLAG.get(c, c) for c in fam_countries]
    pick = st.segmented_control("País", opts, default="🌏 Todos") or "🌏 Todos"
    sel_country = None if pick == "🌏 Todos" else next(c for c in fam_countries if COUNTRY_FLAG.get(c, c) == pick)

n = st.selectbox("Período", [3, 6, 12], index=1, format_func=lambda k: f"últimos {k} meses")

native = sel_country is not None
cur = COUNTRY_CCY.get(sel_country, base) if native else base
res = dash.category_averages(n_months=n, country=sel_country, native=native)
cats = {c["id"]: c for c in ctx["categories"]}

if res["months"] == 0:
    st.info("Ainda não há lançamentos suficientes para calcular médias. Lance ou importe alguns meses primeiro.")
else:
    st.caption(f"Baseado em **{res['months']}** mês(es) com lançamentos.")

    # ---- média total por mês (destaque) ----
    st.markdown(
        '<div class="kpi-grid"><div class="kpi kpi-hero">'
        '<div class="kpi-l">Média de gasto por mês (total)</div>'
        f'<div class="kpi-v">{format_money(res["total_avg"], cur)}</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # ---- por categoria (ordenado) ----
    rows = sorted(res["per_cat_avg"].items(), key=lambda kv: kv[1], reverse=True)
    data = []
    for cid, avg in rows:
        if avg <= 0:
            continue
        c = cats.get(cid)
        name = f"{c.get('icon', '')} {c['name']}".strip() if c else "Sem categoria"
        data.append((name, round(avg, 2)))

    if data:
        st.subheader(f"Média por categoria ({cur})")
        df = pd.DataFrame({"Categoria": [d[0] for d in data], cur: [d[1] for d in data]}).set_index("Categoria")
        st.bar_chart(df, horizontal=True)
        for name, avg in data:
            st.markdown(f"**{name}** — {format_money(avg, cur)} / mês")

bottom_nav("mais")
