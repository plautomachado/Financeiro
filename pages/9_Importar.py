import streamlit as st

st.set_page_config(page_title="Importar", page_icon="📥",
                   layout="centered", initial_sidebar_state="collapsed")

import io
from datetime import date

import pandas as pd

from src.components.auth import require_auth, sidebar_account
from src.components.ui import inject_css, bottom_nav
from src.services.reference_service import load_context, latest_rate
from src.services.rules_service import list_rules, create_rule, delete_rule, categorize
from src.db.client import get_client

inject_css()
require_auth()
sidebar_account()
ctx = load_context()
base = ctx["base_currency"]
cats = ctx["categories"]
cat_names = [c["name"] for c in cats]
cat_by_name = {c["name"]: c for c in cats}
cat_by_id = {c["id"]: c for c in cats}
members = ctx["members"]
COUNTRY = {"JP": "Japão", "BR": "Brasil", "EU": "Europa", "US": "EUA"}

st.title("📥 Importar extrato")
st.caption("Suba um CSV do banco/cartão. O app tenta categorizar sozinho pelas suas regras, e você revisa antes de gravar.")


def _parse_amt(x):
    if x is None:
        return None
    s = str(x).strip()
    if not s or s.lower() == "nan":
        return None
    neg = s.startswith("-") or s.startswith("(")
    s = s.lstrip("+-").replace("(", "").replace(")", "").replace(" ", "").replace("R$", "").replace("¥", "").replace("€", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


# ---------- padrões dos lançamentos importados ----------
st.subheader("1. Padrões")
d1, d2, d3 = st.columns(3)
member = d1.selectbox("Pessoa", members, format_func=lambda m: m["name"])
currency = d2.selectbox("Moeda", ["BRL", "JPY", "EUR", "USD"],
                        index=["BRL", "JPY", "EUR", "USD"].index(member["default_currency"]))
country = d3.selectbox("País", ["BR", "JP", "EU", "US"],
                       index=["BR", "JP", "EU", "US"].index(member["default_country"]),
                       format_func=lambda c: COUNTRY[c])

# ---------- upload ----------
st.subheader("2. Arquivo CSV")
up = st.file_uploader("Selecione o CSV do extrato", type=["csv"])

if up is not None:
    raw = up.getvalue()
    text = None
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except Exception:
            continue
    df = None
    for sep in [";", ",", "\t"]:
        try:
            cand = pd.read_csv(io.StringIO(text), sep=sep, dtype=str).dropna(how="all")
            if cand.shape[1] >= 2:
                df = cand
                break
        except Exception:
            continue

    if df is None or df.empty:
        st.error("Não consegui ler o arquivo. Confira se é um CSV válido.")
    else:
        st.caption("Prévia do arquivo:")
        st.dataframe(df.head(5), use_container_width=True)
        cols = list(df.columns)

        st.subheader("3. Quais colunas?")
        m1, m2, m3 = st.columns(3)
        c_date = m1.selectbox("Data", cols, index=0)
        c_desc = m2.selectbox("Descrição", cols, index=min(1, len(cols) - 1))
        c_amt = m3.selectbox("Valor", cols, index=min(2, len(cols) - 1))
        neg_is = st.radio("Valores negativos são…", ["Despesas", "Receitas"], horizontal=True)

        if st.button("Preparar lançamentos", type="primary", use_container_width=True):
            rules = list_rules()
            dates = pd.to_datetime(df[c_date], dayfirst=True, errors="coerce").dt.date
            rows = []
            for i in range(len(df)):
                dt = dates.iloc[i]
                amt = _parse_amt(df[c_amt].iloc[i])
                desc = str(df[c_desc].iloc[i])
                if dt is None or pd.isna(dt) or amt is None:
                    continue
                if neg_is == "Despesas":
                    tipo = "Despesa" if amt < 0 else "Receita"
                else:
                    tipo = "Receita" if amt < 0 else "Despesa"
                cid, _ = categorize(desc, rules)
                rows.append({
                    "Importar": True, "Data": dt, "Descrição": desc,
                    "Valor": round(abs(amt), 2), "Tipo": tipo,
                    "Categoria": cat_by_id.get(cid, {}).get("name", ""),
                })
            ignored = len(df) - len(rows)
            st.session_state["import_df"] = pd.DataFrame(rows)
            st.session_state["import_ignored"] = ignored

    # ---------- prévia editável ----------
    if "import_df" in st.session_state and not st.session_state["import_df"].empty:
        st.subheader("4. Revisar e importar")
        if st.session_state.get("import_ignored"):
            st.caption(f"{st.session_state['import_ignored']} linha(s) ignorada(s) (sem data/valor legível).")
        edited = st.data_editor(
            st.session_state["import_df"], use_container_width=True, num_rows="fixed", key="imp_editor",
            column_config={
                "Importar": st.column_config.CheckboxColumn("✓"),
                "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "Descrição": st.column_config.TextColumn("Descrição"),
                "Valor": st.column_config.NumberColumn("Valor", format="%.2f"),
                "Tipo": st.column_config.SelectboxColumn("Tipo", options=["Despesa", "Receita"]),
                "Categoria": st.column_config.SelectboxColumn("Categoria", options=[""] + cat_names),
            },
        )
        n = int(edited["Importar"].sum())
        if st.button(f"✅ Importar {n} lançamento(s)", type="primary", use_container_width=True, disabled=(n == 0)):
            rate = 1.0 if currency == base else (latest_rate(currency, base) or 1.0)
            payloads = []
            for _, r in edited[edited["Importar"]].iterrows():
                cat = cat_by_name.get(r["Categoria"])
                payloads.append({
                    "household_id": ctx["household_id"], "member_id": member["id"],
                    "type": "expense" if r["Tipo"] == "Despesa" else "income",
                    "amount_original": float(r["Valor"]), "currency_original": currency,
                    "country": country, "exchange_rate": float(rate), "base_currency": base,
                    "category_id": (cat["id"] if cat else None),
                    "description": str(r["Descrição"])[:200],
                    "occurred_on": r["Data"].isoformat(),
                })
            if payloads:
                get_client().table("transactions").insert(payloads).execute()
                st.session_state.pop("import_df", None)
                st.success(f"{len(payloads)} lançamentos importados! 🎉")
                st.balloons()
                st.rerun()

# ---------- regras de categorização ----------
st.divider()
st.subheader("🏷️ Regras de categorização")
st.caption("Quando a descrição CONTÉM um texto, a categoria é aplicada sozinha (aqui e no lançamento por texto).")

exp_cats = [c for c in cats if c["kind"] in ("expense", "income", "both")]
with st.expander("➕ Nova regra"):
    mt = st.text_input("Se a descrição contém…", placeholder="Ex.: UBER, IFOOD, ALUGUEL", key="rule_txt")
    rc = st.selectbox("→ usar a categoria", exp_cats, format_func=lambda c: f"{c.get('icon', '')} {c['name']}".strip(), key="rule_cat")
    if st.button("Salvar regra", type="primary", key="rule_save"):
        if mt.strip():
            create_rule(mt.strip(), rc["id"])
            st.success("Regra criada!")
            st.rerun()
        else:
            st.warning("Informe o texto da regra.")

for r in list_rules():
    cat = cat_by_id.get(r["category_id"])
    row = st.columns([6, 1])
    row[0].markdown(f"“**{r['match_text']}**” → {cat.get('icon', '') if cat else ''} {cat['name'] if cat else '—'}")
    if row[1].button("🗑", key=f"delr_{r['id']}"):
        delete_rule(r["id"])
        st.rerun()

bottom_nav("mais")
