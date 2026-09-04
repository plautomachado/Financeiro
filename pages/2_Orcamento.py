import streamlit as st

st.set_page_config(page_title="Orçamento", page_icon="📊",
                   layout="centered", initial_sidebar_state="collapsed")

from datetime import date

from src.components.auth import require_auth, sidebar_account
from src.components.ui import inject_css, bottom_nav
from src.services.reference_service import load_context
from src.services.budget_service import (
    budget_status, upsert_budget, delete_budget, COUNTRY_CCY,
    total_status, upsert_total_budget,
)
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

# ---------- Teto do mês (orçamento TOTAL, sem dividir por categoria) ----------
tcur = COUNTRY_CCY.get(sel_country, base) if sel_country else base
ts = total_status(year, month, sel_country)
with st.container(border=True):
    st.markdown("#### 🎯 Teto do mês")
    st.caption("Quanto você quer gastar no mês **todo** (não precisa dividir por categoria).")
    if sel_country is None:
        if ts:
            emoji, label = STATUS[ts["status"]]
            st.markdown(f"**{format_money(ts['spent'], tcur)} / {format_money(ts['planned'], tcur)}** &nbsp; {emoji} {label}")
            st.progress(min(ts["usage"] / 100, 1.0),
                        text=(f"{format_pct(ts['usage'])} usado · disponível {format_money(ts['available'], tcur)} · "
                              f"projeção de fechamento {format_money(ts['projection'], tcur)}"))
        else:
            st.caption("Escolha um país (🇧🇷/🇯🇵) acima para definir o teto de cada um.")
    else:
        cur_opts = [tcur] + [c for c in ["JPY", "BRL", "EUR", "USD"] if c != tcur]
        cc1, cc2 = st.columns([1, 2])
        idx = cur_opts.index(ts["src_currency"]) if ts and ts.get("src_currency") in cur_opts else 0
        cap_cur = cc1.selectbox("Moeda", cur_opts, index=idx, key="cap_cur")
        step = 1000.0 if cap_cur == "JPY" else (1.0 if cap_cur in ("EUR", "USD") else 100.0)
        cap_in = cc2.number_input(f"Meta do mês ({cap_cur})", min_value=0.0, step=step,
                                  value=float(ts["src_amount"]) if ts and ts.get("src_amount") else 0.0, key="cap_input")
        b1, b2 = st.columns([3, 1])
        if b1.button("Salvar teto", type="primary", use_container_width=True, key="cap_save"):
            upsert_total_budget(year, month, cap_in, cap_cur, sel_country)
            st.rerun()
        if ts and ts.get("id") and b2.button("🗑", key="cap_del", use_container_width=True):
            delete_budget(ts["id"])
            st.rerun()
        if ts:
            emoji, label = STATUS[ts["status"]]
            st.progress(min(ts["usage"] / 100, 1.0),
                        text=(f"{format_money(ts['spent'], tcur)} de {format_money(ts['planned'], tcur)} · "
                              f"{format_pct(ts['usage'])} {emoji} {label} · disponível {format_money(ts['available'], tcur)} · "
                              f"projeção {format_money(ts['projection'], tcur)}"))
            if ts.get("src_currency") and ts["src_currency"] != tcur:
                st.caption(f"↔ Definido em {format_money(ts['src_amount'], ts['src_currency'])} — "
                           f"convertido pra {tcur} no câmbio de hoje.")

# ---------- Orçamento por categoria (opcional, mais detalhado) ----------
st.subheader("Por categoria (opcional)")
rows = budget_status(year, month, sel_country)
if not rows:
    st.caption("Sem orçamentos por categoria ainda — dá pra usar só o teto acima, ou detalhar em **➕ Definir orçamento** abaixo.")

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
    if r.get("src_currency") and r["src_currency"] != cur:
        st.caption(f"↔ definido em {format_money(r['src_amount'], r['src_currency'])}")

st.divider()
with st.expander("➕ Definir / editar orçamento"):
    # país do orçamento (na visão "Todos", escolhe; senão usa o país selecionado)
    if sel_country:
        b_country = sel_country
        if len(fam_countries) > 1:
            st.caption(f"Orçamento para **{COUNTRY_FLAG.get(b_country, b_country)}**")
    else:
        b_country = st.selectbox("País", fam_countries, format_func=lambda c: COUNTRY_FLAG.get(c, c))
    native = COUNTRY_CCY.get(b_country, base)
    cats = [c for c in ctx["categories"] if c["kind"] in ("expense", "both")]
    csel = st.selectbox("Categoria", cats, format_func=lambda c: f"{c.get('icon', '')} {c['name']}".strip())
    cur_opts = [native] + [c for c in ["JPY", "BRL", "EUR", "USD"] if c != native]
    b_cur = st.selectbox("Moeda", cur_opts, key="catbud_cur")
    step = 1000.0 if b_cur == "JPY" else (1.0 if b_cur in ("EUR", "USD") else 100.0)
    val = st.number_input(f"Planejado para o mês ({b_cur})", min_value=0.0, step=step)
    if st.button("Salvar orçamento", type="primary"):
        upsert_budget(year, month, csel["id"], val, b_cur, b_country)
        st.success("Orçamento salvo.")
        st.rerun()

bottom_nav("orcamento")
