import streamlit as st

st.set_page_config(page_title="Orçamento", page_icon="📊",
                   layout="centered", initial_sidebar_state="collapsed")

from datetime import date

from src.components.auth import require_auth, sidebar_account
from src.components.ui import inject_css, bottom_nav
from src.services.reference_service import load_context
from src.services.budget_service import budget_status, upsert_budget, delete_budget, COUNTRY_CCY
from src.utils.formatting import format_money, format_pct
from src.utils.dates import month_name

inject_css()
require_auth()
sidebar_account()
ctx = load_context()
base = ctx["base_currency"]

COUNTRY_FLAG = {"BR": "🇧🇷 Brasil", "JP": "🇯🇵 Japão", "EU": "🇪🇺 Europa", "US": "🇺🇸 EUA"}

st.title("📊 Orçamento")

today = date.today()
c1, c2 = st.columns(2)
month = c1.selectbox("Mês", list(range(1, 13)), index=today.month - 1, format_func=month_name)
year = c2.selectbox("Ano", [today.year - 1, today.year, today.year + 1], index=1)

# países da família (adaptável: família de 1 moeda nem vê o seletor)
fam_countries = sorted({m["default_country"] for m in ctx["members"]})
sel_country = fam_countries[0] if fam_countries else "BR"
if len(fam_countries) > 1:
    opts = ["🌏 Todos"] + [COUNTRY_FLAG.get(c, c) for c in fam_countries]
    pick = st.segmented_control("País", opts, default="🌏 Todos") or "🌏 Todos"
    sel_country = None if pick == "🌏 Todos" else next(c for c in fam_countries if COUNTRY_FLAG.get(c, c) == pick)

STATUS = {"ok": ("🟢", "Normal"), "warn": ("🟡", "Atenção"), "over": ("🔴", "Acima do orçamento")}

rows = budget_status(year, month, sel_country)
if not rows:
    st.info("Nenhum orçamento definido para este período. Use **➕ Definir orçamento** abaixo.")

# total (útil principalmente na visão "Todos", tudo em R$)
if rows:
    tot_plan = sum(r["planned"] for r in rows)
    tot_spent = sum(r["spent"] for r in rows)
    tcur = base if sel_country is None else COUNTRY_CCY.get(sel_country, base)
    t1, t2 = st.columns(2)
    t1.metric("Planejado (total)", format_money(tot_plan, tcur))
    t2.metric("Gasto (total)", format_money(tot_spent, tcur))

for r in rows:
    emoji, label = STATUS[r["status"]]
    cur = r["currency"]
    flag = (COUNTRY_FLAG.get(r["country"], "").split(" ")[0] + " ") if sel_country is None else ""
    head = st.columns([6, 1])
    head[0].markdown(f"**{flag}{r['icon']} {r['category']}** — "
                     f"{format_money(r['spent'], cur)} / {format_money(r['planned'], cur)} &nbsp; {emoji} {label}")
    with head[1].popover("🗑"):
        st.caption("Excluir este orçamento?")
        if st.button("Confirmar", key=f"delb_{r['id']}", type="primary"):
            delete_budget(r["id"])
            st.rerun()
    st.progress(
        min(r["usage"] / 100, 1.0),
        text=(f"{format_pct(r['usage'])} usado · disponível {format_money(r['available'], cur)} · "
              f"projeção de fechamento {format_money(r['projection'], cur)}"),
    )

st.divider()
with st.expander("➕ Definir / editar orçamento"):
    # país do orçamento (na visão "Todos", escolhe; senão usa o país selecionado)
    if sel_country:
        b_country = sel_country
        if len(fam_countries) > 1:
            st.caption(f"Orçamento para **{COUNTRY_FLAG.get(b_country, b_country)}**")
    else:
        b_country = st.selectbox("País", fam_countries, format_func=lambda c: COUNTRY_FLAG.get(c, c))
    b_cur = COUNTRY_CCY.get(b_country, base)
    cats = [c for c in ctx["categories"] if c["kind"] in ("expense", "both")]
    csel = st.selectbox("Categoria", cats, format_func=lambda c: f"{c.get('icon', '')} {c['name']}".strip())
    step = 1000.0 if b_cur == "JPY" else 100.0
    val = st.number_input(f"Planejado para o mês ({b_cur})", min_value=0.0, step=step)
    if st.button("Salvar orçamento", type="primary"):
        upsert_budget(year, month, csel["id"], val, b_cur, b_country)
        st.success("Orçamento salvo.")
        st.rerun()

bottom_nav("orcamento")
