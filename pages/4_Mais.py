import streamlit as st

st.set_page_config(page_title="Mais", page_icon="⚙️",
                   layout="centered", initial_sidebar_state="collapsed")

from datetime import date
import pandas as pd

from src.components.auth import require_auth, sidebar_account
from src.components.ui import inject_css, bottom_nav
from src.services.reference_service import load_context, refresh_context
from src.services.transaction_service import list_transactions
from src.db.client import get_client

inject_css()
require_auth()
sidebar_account()
ctx = load_context()

st.title("⚙️ Mais")

tab1, tab2, tab3, tab4 = st.tabs(["Membros & contas", "Categorias", "Câmbio", "Exportar"])

with tab1:
    st.write("**Membros da família**")
    st.table([{"Nome": m["name"], "País": m["default_country"], "Moeda": m["default_currency"]}
              for m in ctx["members"]])
    st.write("**Contas**")
    st.table([{"Conta": a["name"], "Tipo": a["type"], "País": a["country"], "Moeda": a["currency"]}
              for a in ctx["accounts"]])

with tab2:
    st.table([{"Categoria": f"{c.get('icon', '')} {c['name']}".strip(),
               "Tipo": {"expense": "Despesa", "income": "Receita", "both": "Ambos"}.get(c["kind"], c["kind"])}
              for c in ctx["categories"]])

with tab3:
    st.caption("Taxa usada nas conversões: 1 unidade de *De* equivale a *Taxa* unidades de *Para*.")
    d1, d2, d3 = st.columns(3)
    frm = d1.selectbox("De", ["JPY", "BRL", "EUR", "USD"])
    to = d2.selectbox("Para", ["BRL", "JPY", "EUR", "USD"])
    rate = d3.number_input("Taxa", min_value=0.0, step=0.0001, format="%.4f")
    if st.button("Salvar taxa", type="primary"):
        if frm == to:
            st.warning("Escolha moedas diferentes.")
        elif rate <= 0:
            st.warning("Informe uma taxa maior que zero.")
        else:
            get_client().table("exchange_rates").upsert(
                {"household_id": ctx["household_id"], "from_currency": frm, "to_currency": to,
                 "rate": rate, "rate_date": date.today().isoformat()},
                on_conflict="household_id,from_currency,to_currency,rate_date",
            ).execute()
            refresh_context()
            st.success(f"Taxa salva: 1 {frm} = {rate} {to}")

with tab4:
    st.caption("Baixe todo o histórico de transações (você é o dono dos seus dados).")
    txs = list_transactions(limit=10000)
    if txs:
        df = pd.DataFrame(txs)
        st.download_button("⬇️ Baixar CSV", df.to_csv(index=False).encode("utf-8"),
                           file_name="cofre_transacoes.csv", mime="text/csv",
                           use_container_width=True)
        st.caption(f"{len(txs)} transações.")
    else:
        st.info("Sem transações para exportar ainda.")

st.divider()
st.caption("Cartões, parcelamentos, recorrências e patrimônio chegam na **Fase 2**.")

bottom_nav("mais")
