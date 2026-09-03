import streamlit as st

st.set_page_config(page_title="Recorrências", page_icon="🔁",
                   layout="centered", initial_sidebar_state="collapsed")

from datetime import date

from src.components.auth import require_auth, sidebar_account
from src.components.ui import inject_css, bottom_nav
from src.services.reference_service import load_context
from src.services.recurring_service import (
    list_recurring, create_recurring, update_recurring, deactivate_recurring,
    occurrences_for_month, mark_paid, unmark_paid, to_base,
)
from src.utils.formatting import format_money
from src.utils.dates import month_name

inject_css()
require_auth()
sidebar_account()
ctx = load_context()
base = ctx["base_currency"]
members = {m["id"]: m for m in ctx["members"]}
cats = {c["id"]: c for c in ctx["categories"]}

st.title("🔁 Recorrências")
st.caption("Contas fixas (aluguel, escola, internet, assinaturas) mês a mês: **previsto × pago**.")

today = date.today()
c1, c2 = st.columns(2)
month = c1.selectbox("Mês", list(range(1, 13)), index=today.month - 1, format_func=month_name)
year = c2.selectbox("Ano", [today.year - 1, today.year, today.year + 1], index=1)

occs = occurrences_for_month(year, month)
if not occs:
    st.info("Nenhuma recorrência para este mês. Cadastre em **➕ Nova recorrência** abaixo.")

_unpaid = [o for o in occs if not o["paid"]]
if _unpaid:
    if st.button(f"✓ Marcar {len(_unpaid)} conta(s) como paga(s)", use_container_width=True):
        for o in _unpaid:
            mark_paid(o["recurring"], year, month)
        st.rerun()

prev_total = sum(to_base(o["recurring"]["amount"], o["recurring"]["currency"], base) for o in occs if not o["paid"])
pago_total = sum(float(o["transaction"]["amount_base"] or 0) for o in occs if o["paid"])

for o in occs:
    rec = o["recurring"]
    cat = cats.get(rec.get("category_id"))
    catname = f"{cat.get('icon', '')} {cat['name']}".strip() if cat else "—"
    who = members.get(rec["member_id"], {}).get("name", "—")
    status = "🟢 Pago" if o["paid"] else "🟡 Previsto"
    with st.container(border=True):
        top = st.columns([3, 2])
        top[0].markdown(f"**{rec['description']}**")
        top[1].markdown(f"{format_money(rec['amount'], rec['currency'])} · {status}")
        st.caption(f"{catname} · {who} · vence dia {o['due_date'].day}")
        if o["paid"]:
            if st.button("↩ Desfazer pagamento", key=f"undo_{rec['id']}", use_container_width=True):
                unmark_paid(o["transaction"]["id"])
                st.rerun()
        else:
            if st.button("✓ Marcar como paga", key=f"pay_{rec['id']}", type="primary", use_container_width=True):
                mark_paid(rec, year, month)
                st.rerun()

if occs:
    st.divider()
    t1, t2 = st.columns(2)
    t1.metric("Falta pagar (previsto)", format_money(prev_total, base))
    t2.metric("Já pago no mês", format_money(pago_total, base))

# --------- Nova recorrência ---------
st.divider()
with st.expander("➕ Nova recorrência"):
    desc = st.text_input("Descrição", placeholder="Ex.: Aluguel, Escola, Netflix", key="rec_desc")
    r1, r2 = st.columns([2, 1])
    amount = r1.number_input("Valor", min_value=0.0, step=100.0, key="rec_amt")
    currency = r2.selectbox("Moeda", ["BRL", "JPY", "EUR", "USD"], key="rec_cur")
    member = st.selectbox("Pessoa", ctx["members"], format_func=lambda m: m["name"], key="rec_mem")
    exp_cats = [c for c in ctx["categories"] if c["kind"] in ("expense", "both")]
    cat_sel = st.selectbox("Categoria", exp_cats, format_func=lambda c: f"{c.get('icon', '')} {c['name']}".strip(), key="rec_cat")
    p1, p2 = st.columns(2)
    periodicity = p1.selectbox("Periodicidade", ["monthly", "yearly"],
                               format_func=lambda p: "Mensal" if p == "monthly" else "Anual", key="rec_per")
    due_day = p2.number_input("Dia do vencimento", min_value=1, max_value=31, value=5, key="rec_day")
    s1, s2 = st.columns(2)
    start = s1.date_input("Início", value=date(year, month, 1), format="DD/MM/YYYY", key="rec_start")
    has_end = s2.checkbox("Tem fim?", key="rec_hasend")
    end = st.date_input("Data final", value=date.today(), format="DD/MM/YYYY", key="rec_end") if has_end else None
    auto = st.checkbox("💳 Débito automático (lança sozinho quando vence)", key="rec_auto")
    country = {"JPY": "JP", "BRL": "BR", "EUR": "EU", "USD": "US"}[currency]
    if st.button("Salvar recorrência", type="primary", key="rec_save"):
        if desc.strip() and amount > 0:
            create_recurring(description=desc.strip(), amount=amount, currency=currency, country=country,
                             member_id=member["id"], category_id=cat_sel["id"], periodicity=periodicity,
                             due_day=int(due_day), start_date=start, end_date=end, auto_post=auto)
            st.success("Recorrência criada!")
            st.rerun()
        else:
            st.warning("Preencha descrição e valor.")

# --------- Gerenciar ---------
all_recs = list_recurring(active_only=True)
if all_recs:
    with st.expander("⚙️ Gerenciar recorrências ativas"):
        for d in all_recs:
            auto = bool(d.get("auto_post"))
            g = st.columns([3, 1, 1])
            per = "mensal" if d["periodicity"] == "monthly" else "anual"
            badge = " · 💳 auto" if auto else ""
            g[0].write(f"**{d['description']}** — {format_money(d['amount'], d['currency'])} · {per} · dia {d.get('due_day', '—')}{badge}")
            if g[1].button("→ Manual" if auto else "→ Auto", key=f"auto_{d['id']}"):
                update_recurring(d["id"], {"auto_post": not auto})
                st.rerun()
            if g[2].button("Desativar", key=f"deact_{d['id']}"):
                deactivate_recurring(d["id"])
                st.rerun()

bottom_nav("mais")
