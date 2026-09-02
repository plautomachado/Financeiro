import streamlit as st

st.set_page_config(page_title="Lançar", page_icon="➕",
                   layout="centered", initial_sidebar_state="collapsed")

from datetime import date

from src.components.auth import require_auth, sidebar_account
from src.components.ui import inject_css, bottom_nav
from src.services.reference_service import load_context, latest_rate
from src.services.transaction_service import create_transaction
from src.services.goal_service import list_goals
from src.services.nl_parser import parse_entry
from src.utils.formatting import format_money

inject_css()
require_auth()
sidebar_account()
ctx = load_context()
base = ctx["base_currency"]

st.title("➕ Novo lançamento")

TYPES = {"Despesa": "expense", "Receita": "income", "Aporte": "contribution", "Transferência": "transfer"}
CURRENCIES = ["JPY", "BRL", "EUR", "USD"]
COUNTRIES = ["JP", "BR", "EU", "US"]
COUNTRY_LABELS = {"JP": "Japão", "BR": "Brasil", "EU": "Europa", "US": "EUA"}

# ---------- Lançamento por texto (linguagem natural) ----------
st.caption("⌨️ Lançamento rápido por texto")
with st.form("nl_form"):
    nl_text = st.text_input(
        "texto", label_visibility="collapsed",
        placeholder="ex.: mercado 3850  ·  esposa mercado 185 reais  ·  uber 1200 ontem",
    )
    interpretar = st.form_submit_button("Interpretar", use_container_width=True)
if interpretar and nl_text.strip():
    res = parse_entry(nl_text, ctx["members"], ctx["categories"], base)
    from src.services.rules_service import categorize
    _cid, _ = categorize(nl_text)
    if _cid:
        _c = next((c for c in ctx["categories"] if c["id"] == _cid), None)
        if _c:
            res["category"] = _c
    st.session_state.nl_result = res

res = st.session_state.get("nl_result")
if res:
    type_pt = {v: k for k, v in TYPES.items()}.get(res["type"], res["type"])
    cat_name = res["category"]["name"] if res.get("category") else "—"
    mem_name = res["member"]["name"] if res.get("member") else "—"
    val_txt = format_money(res["amount"], res["currency"]) if res.get("amount") else "—"
    st.info(f"**{type_pt}** · {val_txt} · {cat_name} · {mem_name} · "
            f"{COUNTRY_LABELS.get(res['country'], res['country'])} · {res['date'].strftime('%d/%m/%Y')}")
    for w in res.get("warnings", []):
        st.caption("⚠️ " + w)
    can_save = bool(res.get("amount")) and bool(res.get("member"))
    b1, b2 = st.columns(2)
    if b1.button("✅ Confirmar", type="primary", use_container_width=True, disabled=not can_save):
        create_transaction(
            type=res["type"], amount_original=res["amount"], currency_original=res["currency"],
            country=res["country"], member_id=res["member"]["id"],
            category_id=(res["category"]["id"] if res.get("category") else None),
            description=res["raw"], occurred_on=res["date"],
        )
        st.session_state.pop("nl_result", None)
        st.success("Lançado por texto! ✅")
        st.balloons()
        st.rerun()
    if b2.button("✖️ Cancelar", use_container_width=True):
        st.session_state.pop("nl_result", None)
        st.rerun()

st.divider()
st.caption("ou preencha manualmente")

type_label = st.segmented_control("Tipo", list(TYPES.keys()), default="Despesa") or "Despesa"
ttype = TYPES[type_label]

# Pessoa define os padrões inteligentes
members = ctx["members"]
member_names = [m["name"] for m in members]
msel = st.segmented_control("Pessoa", member_names, default=member_names[0]) or member_names[0]
member = next(m for m in members if m["name"] == msel)
def_cur = member["default_currency"]
def_country = member["default_country"]

col1, col2 = st.columns([2, 1])
amount = col1.number_input("Valor", min_value=0.0, step=100.0, format="%.2f")
currency = col2.selectbox("Moeda", CURRENCIES, index=CURRENCIES.index(def_cur))

country = st.selectbox("País", COUNTRIES, index=COUNTRIES.index(def_country),
                       format_func=lambda c: COUNTRY_LABELS[c])

# Categoria (despesa/receita) ou Meta (aporte)
category_id = None
goal_id = None
if ttype in ("expense", "income"):
    kind = "expense" if ttype == "expense" else "income"
    cats = [c for c in ctx["categories"] if c["kind"] in (kind, "both")]
    if cats:
        csel = st.selectbox("Categoria", cats, format_func=lambda c: f"{c.get('icon', '')} {c['name']}".strip())
        category_id = csel["id"]
elif ttype == "contribution":
    goals = list_goals()
    if goals:
        gsel = st.selectbox("Meta", goals, format_func=lambda g: g["name"])
        goal_id = gsel["id"]
    else:
        st.info("Cadastre uma meta antes de registrar aportes.")

accounts = [None] + ctx["accounts"]
acc = st.selectbox("Conta / cartão", accounts,
                   format_func=lambda a: "—" if a is None else f"{a['name']} ({a['currency']})")
account_id = acc["id"] if acc else None

occurred = st.date_input("Data", value=date.today(), format="DD/MM/YYYY")
desc = st.text_input("Descrição (opcional)")

# Prévia do câmbio
rate = 1.0 if currency == base else (latest_rate(currency, base) or 1.0)
if currency != base and amount > 0:
    st.caption(f"Câmbio 1 {currency} = {rate} {base}  →  equivale a **{format_money(amount * rate, base)}**")

if st.button("Salvar lançamento", type="primary", use_container_width=True):
    if amount <= 0:
        st.warning("Informe um valor maior que zero.")
    else:
        try:
            create_transaction(
                type=ttype, amount_original=amount, currency_original=currency,
                country=country, member_id=member["id"], category_id=category_id,
                goal_id=goal_id, account_id=account_id, description=desc or None,
                occurred_on=occurred,
            )
            st.success(f"Lançado: {format_money(amount, currency)} · {msel} · {type_label}")
            st.balloons()
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")

bottom_nav("lancar")
