import streamlit as st

st.set_page_config(page_title="Cartões", page_icon="💳",
                   layout="centered", initial_sidebar_state="collapsed")

from datetime import date

from src.components.auth import require_auth, sidebar_account
from src.components.ui import inject_css, bottom_nav
from src.services.reference_service import load_context
from src.services.card_service import (
    list_cards, create_card, deactivate_card, create_installment, list_installments,
)
from src.utils.formatting import format_money

inject_css()
require_auth()
sidebar_account()
ctx = load_context()

st.title("💳 Cartões & parcelas")

# ---------- Cartões ----------
st.subheader("Meus cartões")
cards = list_cards()
if not cards:
    st.caption("Nenhum cartão cadastrado ainda.")
for c in cards:
    with st.container(border=True):
        st.markdown(f"**{c['name']}** · {c['currency']}")
        lim = format_money(c["card_limit"], c["currency"]) if c.get("card_limit") else "—"
        st.caption(f"Limite {lim} · fecha dia {c.get('closing_day', '—')} · vence dia {c.get('due_day', '—')}")
        if st.button("Desativar", key=f"delc_{c['id']}"):
            deactivate_card(c["id"])
            st.rerun()

with st.expander("➕ Novo cartão"):
    name = st.text_input("Nome do cartão", key="cn", placeholder="Ex.: Nubank, Rakuten")
    a, b = st.columns(2)
    cur = a.selectbox("Moeda", ["BRL", "JPY", "EUR", "USD"], key="cc")
    lim = b.number_input("Limite (opcional)", min_value=0.0, step=100.0, key="cl")
    d, e = st.columns(2)
    close = d.number_input("Dia de fechamento", min_value=1, max_value=31, value=1, key="ccl")
    due = e.number_input("Dia de vencimento", min_value=1, max_value=31, value=10, key="cdu")
    owner = st.selectbox("Titular", ctx["members"], format_func=lambda m: m["name"], key="co")
    if st.button("Salvar cartão", type="primary", key="csave"):
        if name.strip():
            create_card(name=name.strip(), currency=cur, card_limit=(lim or None),
                        closing_day=int(close), due_day=int(due), member_id=owner["id"])
            st.success("Cartão salvo!")
            st.rerun()
        else:
            st.warning("Informe o nome do cartão.")

# ---------- Compra parcelada ----------
st.divider()
st.subheader("Nova compra parcelada")
desc = st.text_input("Descrição", placeholder="Ex.: Geladeira", key="i_desc")
c1, c2 = st.columns([2, 1])
total = c1.number_input("Valor total", min_value=0.0, step=100.0, key="i_total")
cur2 = c2.selectbox("Moeda", ["BRL", "JPY", "EUR", "USD"], key="i_cur")
c3, c4 = st.columns(2)
nparc = c3.number_input("Nº de parcelas", min_value=1, max_value=48, value=10, key="i_n")
first = c4.date_input("1ª parcela", value=date.today(), format="DD/MM/YYYY", key="i_first")
who = st.selectbox("Pessoa", ctx["members"], format_func=lambda m: m["name"], key="i_who")
exp_cats = [c for c in ctx["categories"] if c["kind"] in ("expense", "both")]
cat = st.selectbox("Categoria", exp_cats, format_func=lambda c: f"{c.get('icon', '')} {c['name']}".strip(), key="i_cat")
card = st.selectbox("Cartão (opcional)", [None] + cards,
                    format_func=lambda x: "—" if x is None else x["name"], key="i_card")

if total > 0:
    st.caption(f"➜ Vai gerar **{int(nparc)}×** de ~{format_money(round(total / int(nparc), 2), cur2)}, "
               f"a partir de {first.strftime('%m/%Y')}.")

if st.button("Gerar parcelas", type="primary", use_container_width=True, key="i_save"):
    if desc.strip() and total > 0:
        country = {"JPY": "JP", "BRL": "BR", "EUR": "EU", "USD": "US"}[cur2]
        _, parcela = create_installment(
            description=desc.strip(), total_amount=total, currency=cur2, country=country,
            member_id=who["id"], installments_count=int(nparc), first_date=first,
            category_id=cat["id"], credit_card_id=(card["id"] if card else None),
        )
        st.success(f"Geradas {int(nparc)} parcelas de {format_money(parcela, cur2)}! Aparecem no mês de cada uma.")
        st.balloons()
    else:
        st.warning("Preencha descrição e valor.")

# ---------- Parcelamentos recentes ----------
insts = list_installments()
if insts:
    with st.expander("📋 Parcelamentos recentes"):
        for it in insts:
            st.write(f"**{it['description']}** — {format_money(it['total_amount'], it['currency'])} "
                     f"em {it['installments_count']}×")

bottom_nav("mais")
