import streamlit as st

st.set_page_config(page_title="Mais", page_icon="⚙️",
                   layout="centered", initial_sidebar_state="collapsed")

from datetime import date
import pandas as pd

from src.components.auth import require_auth, sidebar_account, account_section
from src.components.ui import inject_css, bottom_nav
from src.services.reference_service import (
    load_context, refresh_context, create_category, deactivate_category,
    reorder_categories, update_category,
)
from src.services.transaction_service import list_transactions
from src.services.currency_service import current_rates_to_brl, update_rates_to_brl
from src.utils.formatting import format_money
from src.db.client import get_client

inject_css()
require_auth()
sidebar_account()
ctx = load_context()

st.title("⚙️ Mais")

account_section()
st.divider()

st.page_link("pages/5_Recorrencias.py", label="🔁 Recorrências", use_container_width=True)
st.page_link("pages/6_Cartoes.py", label="💳 Cartões & parcelas", use_container_width=True)
st.page_link("pages/7_Relatorio.py", label="📄 Relatório mensal", use_container_width=True)
st.page_link("pages/10_Medias.py", label="📊 Médias mensais", use_container_width=True)
st.page_link("pages/8_Patrimonio.py", label="🏦 Patrimônio", use_container_width=True)
st.page_link("pages/9_Importar.py", label="📥 Importar extrato + regras", use_container_width=True)

tab1, tab2, tab3, tab4 = st.tabs(["Membros & contas", "Categorias", "Câmbio", "Exportar"])

with tab1:
    st.write("**Membros da família**")
    st.table([{"Nome": m["name"], "País": m["default_country"], "Moeda": m["default_currency"]}
              for m in ctx["members"]])
    st.write("**Contas**")
    st.table([{"Conta": a["name"], "Tipo": a["type"], "País": a["country"], "Moeda": a["currency"]}
              for a in ctx["accounts"]])

with tab2:
    with st.expander("➕ Nova categoria"):
        ncn = st.text_input("Nome", key="newcat", placeholder="Ex.: Bônus, Freela Arq")
        nck = st.selectbox("Tipo", ["expense", "income"],
                           format_func=lambda k: "Despesa" if k == "expense" else "Receita", key="newcatk")
        nci = st.text_input("Ícone (emoji, opcional)", key="newcati")
        if st.button("Adicionar categoria", type="primary", key="addcat"):
            if ncn.strip():
                create_category(ncn.strip(), nck, nci.strip() or None)
                refresh_context()
                st.success("Categoria adicionada!")
                st.rerun()
            else:
                st.warning("Informe o nome.")
    st.caption("Arraste em **↕️ Reordenar** pra mudar a ordem · ✏️ renomear · ✖ desativar.")
    cats_sorted = ctx["categories"]

    # ---- Reordenar arrastando e soltando ----
    with st.expander("↕️ Reordenar (arraste e solte)"):
        try:
            from streamlit_sortables import sort_items
            label_to_id, labels = {}, []
            for c in cats_sorted:
                lbl = f"{c.get('icon', '')} {c['name']}".strip()
                while lbl in label_to_id:      # garante rótulo único
                    lbl += " "
                label_to_id[lbl] = c["id"]
                labels.append(lbl)
            new_labels = sort_items(labels, direction="vertical", key="cat_sort")
            if new_labels and list(new_labels) != labels:
                st.caption("Ordem alterada — clique para salvar:")
                if st.button("💾 Salvar nova ordem", type="primary", key="save_cat_order"):
                    reorder_categories([label_to_id[l] for l in new_labels])
                    refresh_context()
                    st.rerun()
        except Exception:
            st.caption("Recurso de arrastar ainda carregando (aguarde o app atualizar).")

    for c in cats_sorted:
        tag = {"expense": "Despesa", "income": "Receita", "both": "Ambos"}.get(c["kind"], c["kind"])
        row = st.columns([6, 1, 1])
        row[0].markdown(f"{c.get('icon', '')} **{c['name']}** — {tag}")
        if row[1].button("✏️", key=f"editcat_{c['id']}"):
            st.session_state["edit_cat_id"] = c["id"]
            st.rerun()
        if row[2].button("✖", key=f"delcat_{c['id']}"):
            deactivate_category(c["id"])
            refresh_context()
            st.rerun()
        if st.session_state.get("edit_cat_id") == c["id"]:
            with st.container(border=True):
                en = st.text_input("Novo nome", value=c["name"], key=f"ecn_{c['id']}")
                ei = st.text_input("Ícone (emoji)", value=c.get("icon") or "", key=f"eci_{c['id']}")
                eb1, eb2 = st.columns(2)
                if eb1.button("Salvar", type="primary", key=f"ecs_{c['id']}", use_container_width=True):
                    if en.strip():
                        update_category(c["id"], {"name": en.strip(), "icon": ei.strip() or None})
                        st.session_state.pop("edit_cat_id", None)
                        refresh_context()
                        st.rerun()
                    else:
                        st.warning("O nome não pode ficar vazio.")
                if eb2.button("Cancelar", key=f"ecc_{c['id']}", use_container_width=True):
                    st.session_state.pop("edit_cat_id", None)
                    st.rerun()

with tab3:
    st.write("**Cotações automáticas → Real**")
    r = current_rates_to_brl()
    m1, m2, m3 = st.columns(3)
    m1.metric("1 USD 💵", format_money(r.get("USD", 0), "BRL"))
    m2.metric("1 EUR 💶", format_money(r.get("EUR", 0), "BRL"))
    m3.metric("¥100 💴", format_money(r.get("JPY", 0) * 100, "BRL"))
    if st.button("🔄 Atualizar cotação agora", type="primary", use_container_width=True):
        if update_rates_to_brl():
            st.success("Cotações atualizadas!")
            st.rerun()
        else:
            st.error("Não consegui buscar a cotação agora. Tente mais tarde ou use a taxa manual abaixo.")
    st.caption("Atualiza sozinho 1x por dia. Fontes: open.er-api.com / frankfurter.dev.")

    st.divider()
    with st.expander("✏️ Definir taxa manual (sobrescreve a do dia)"):
        d1, d2, d3 = st.columns(3)
        frm = d1.selectbox("De", ["JPY", "BRL", "EUR", "USD"])
        to = d2.selectbox("Para", ["BRL", "JPY", "EUR", "USD"])
        rate = d3.number_input("Taxa", min_value=0.0, step=0.0001, format="%.4f")
        if st.button("Salvar taxa manual"):
            if frm == to:
                st.warning("Escolha moedas diferentes.")
            elif rate <= 0:
                st.warning("Informe uma taxa maior que zero.")
            else:
                get_client().table("exchange_rates").upsert(
                    {"household_id": ctx["household_id"], "from_currency": frm, "to_currency": to,
                     "rate": rate, "rate_date": date.today().isoformat(), "source": "manual"},
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
