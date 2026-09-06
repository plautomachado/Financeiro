"""Lista de lançamentos com editar/excluir (reutilizada no Início e em Lançamentos)."""
from datetime import date

import streamlit as st

from src.services.reference_service import latest_rate
from src.services.transaction_service import delete_transaction, update_transaction
from src.utils.formatting import format_money

_TYPES = {"Despesa": "expense", "Receita": "income", "Aporte": "contribution", "Transferência": "transfer"}
_CURR = ["JPY", "BRL", "EUR", "USD"]
_CTRY = ["JP", "BR", "EU", "US"]
_FLAG = {"BR": "🇧🇷 Brasil", "JP": "🇯🇵 Japão", "EU": "🇪🇺 Europa", "US": "🇺🇸 EUA"}
_SIGN = {"expense": "−", "income": "+", "contribution": "→", "transfer": "↔"}


def render_edit_form(t, ctx, base, key_prefix="tx"):
    edit_key = f"{key_prefix}_edit_id"
    with st.container(border=True):
        st.caption("✏️ Editar lançamento")
        e1, e2 = st.columns(2)
        etype = e1.selectbox("Tipo", list(_TYPES.keys()),
                             index=list(_TYPES.values()).index(t["type"]) if t["type"] in _TYPES.values() else 0,
                             key=f"{key_prefix}_et_{t['id']}")
        eval_ = e2.number_input("Valor", min_value=0.0, value=float(t["amount_original"] or 0),
                                step=100.0, key=f"{key_prefix}_ev_{t['id']}")
        e3, e4 = st.columns(2)
        ecur = e3.selectbox("Moeda", _CURR, index=_CURR.index(t["currency_original"]) if t["currency_original"] in _CURR else 0,
                            key=f"{key_prefix}_ec_{t['id']}")
        ectry = e4.selectbox("País", _CTRY, index=_CTRY.index(t["country"]) if t["country"] in _CTRY else 0,
                             format_func=lambda c: _FLAG.get(c, c), key=f"{key_prefix}_ectry_{t['id']}")
        ttype = _TYPES[etype]
        cat_id = t.get("category_id")
        if ttype in ("expense", "income"):
            cat_opts = [None] + [c for c in ctx["categories"] if c["kind"] in (ttype, "both")]
            cur_cat = next((c for c in ctx["categories"] if c["id"] == t.get("category_id")), None)
            csel = st.selectbox("Categoria", cat_opts,
                                index=cat_opts.index(cur_cat) if cur_cat in cat_opts else 0,
                                format_func=lambda c: "—" if c is None else f"{c.get('icon', '')} {c['name']}".strip(),
                                key=f"{key_prefix}_ecat_{t['id']}")
            cat_id = csel["id"] if csel else None
        mem_opts = ctx["members"]
        msel = st.selectbox("Pessoa", mem_opts,
                            index=next((i for i, m in enumerate(mem_opts) if m["id"] == t["member_id"]), 0),
                            format_func=lambda m: m["name"], key=f"{key_prefix}_emem_{t['id']}")
        e5, e6 = st.columns(2)
        edate = e5.date_input("Data", value=date.fromisoformat(t["occurred_on"][:10]),
                              format="DD/MM/YYYY", key=f"{key_prefix}_ed_{t['id']}")
        edesc = e6.text_input("Descrição", value=t.get("description") or "", key=f"{key_prefix}_edesc_{t['id']}")
        bb1, bb2 = st.columns(2)
        if bb1.button("💾 Salvar", type="primary", use_container_width=True, key=f"{key_prefix}_esave_{t['id']}"):
            rate = 1.0 if ecur == base else (latest_rate(ecur, base) or float(t.get("exchange_rate") or 1.0))
            update_transaction(t["id"], {
                "type": ttype, "amount_original": float(eval_), "currency_original": ecur,
                "exchange_rate": float(rate), "country": ectry, "category_id": cat_id,
                "member_id": msel["id"], "description": (edesc or None),
                "occurred_on": edate.isoformat(),
            })
            st.session_state.pop(edit_key, None)
            st.success("Lançamento atualizado!")
            st.rerun()
        if bb2.button("Cancelar", use_container_width=True, key=f"{key_prefix}_ecancel_{t['id']}"):
            st.session_state.pop(edit_key, None)
            st.rerun()


def render_tx_list(txs, ctx, base, key_prefix="tx"):
    """Renderiza uma lista de lançamentos, cada um com ✏️ editar e 🗑 excluir."""
    edit_key = f"{key_prefix}_edit_id"
    mem = {m["id"]: m["name"] for m in ctx["members"]}
    cat = {c["id"]: f"{c.get('icon', '')} {c['name']}".strip() for c in ctx["categories"]}
    if not txs:
        st.caption("Nenhum lançamento neste período.")
        return
    for t in txs:
        desc = t.get("description") or cat.get(t.get("category_id"), "—")
        dd = t["occurred_on"][8:10] + "/" + t["occurred_on"][5:7]
        row = st.columns([5, 1, 1])
        row[0].markdown(
            f"{_SIGN.get(t['type'], '')}{format_money(t['amount_original'], t['currency_original'])} "
            f"· {desc} · {mem.get(t['member_id'], '—')} · {dd}"
        )
        if row[1].button("✏️", key=f"{key_prefix}_editbtn_{t['id']}"):
            st.session_state[edit_key] = t["id"]
            st.rerun()
        with row[2].popover("🗑"):
            st.caption("Excluir este lançamento?")
            if st.button("Confirmar exclusão", key=f"{key_prefix}_del_{t['id']}", type="primary"):
                delete_transaction(t["id"])
                st.session_state.pop(edit_key, None)
                st.rerun()
        if st.session_state.get(edit_key) == t["id"]:
            render_edit_form(t, ctx, base, key_prefix)
