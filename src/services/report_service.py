"""Relatório mensal + insights automáticos (frases geradas a partir dos dados)."""
from src.services.reference_service import load_context
from src.services.transaction_service import list_transactions
from src.services import dashboard_service as dash
from src.services.budget_service import budget_status, COUNTRY_CCY
from src.services.goal_service import list_goals, goal_progress
from src.utils.dates import prev_month
from src.utils.formatting import format_money, format_pct


def _pct_change(cur, prev):
    if not prev:
        return None
    return (cur - prev) / prev * 100


def build(year, month, country=None):
    """country=None -> família toda em R$ (base). country='JP'/'BR' -> só o país, na moeda nativa."""
    ctx = load_context()
    base = ctx["base_currency"]
    cats = ctx["categories"]
    members = ctx["members"]
    native = country is not None
    cur = COUNTRY_CCY.get(country, base) if native else base

    s = dash.summary(year, month, country=country, native=native)
    txs = s["_txs"]
    prev = s["prev"]
    py, pm = prev_month(year, month)
    ptxs = list_transactions(year=py, month=pm, country=country)

    cat_now = dash.by_category(txs, cats, native=native)
    cat_prev = dash.by_category(ptxs, cats, native=native)
    by_mem = dash.by_member(txs, members, native=native)
    by_ctry = dash.by_country(txs) if country is None else {}
    budgets = budget_status(year, month, country)
    goals = [(g, goal_progress(g)) for g in list_goals()]

    return {
        "summary": s, "prev": prev, "by_category": cat_now, "by_member": by_mem,
        "by_country": by_ctry, "budgets": budgets, "goals": goals,
        "base": cur, "currency": cur, "country": country,
        "insights": _insights(s, cat_now, cat_prev, by_ctry, budgets, goals, cur),
    }


def _insights(s, cat_now, cat_prev, ctry, budgets, goals, base):
    out = []
    def fm(v):
        return format_money(v, base)

    if s["receitas"] > 0:
        out.append(("💰", f"A família poupou {format_pct(s['taxa_economia'])} da receita este mês."))

    if s["saldo_livre"] < -0.005:
        out.append(("⚠️", f"As despesas e aportes superaram a receita em {fm(abs(s['saldo_livre']))}."))
    elif s["receitas"] > 0:
        out.append(("✅", f"Sobrou {fm(s['saldo_livre'])} de saldo livre no mês."))

    if s["aportes"] > 0:
        out.append(("🐷", f"Vocês guardaram {fm(s['aportes'])} para as metas."))

    if cat_now:
        name, val = next(iter(cat_now.items()))
        share = (val / s["despesas"] * 100) if s["despesas"] else 0
        out.append(("🏷️", f"Maior gasto: {name} — {fm(val)} ({format_pct(share, 0)} das despesas)."))

    movers = []
    for name, val in cat_now.items():
        ch = _pct_change(val, cat_prev.get(name, 0))
        if ch is not None and abs(ch) >= 15:
            movers.append((abs(ch), name, ch))
    if movers:
        movers.sort(reverse=True)
        _, name, ch = movers[0]
        if ch > 0:
            out.append(("📈", f"Gastos com {name} aumentaram {format_pct(ch, 0)} vs. o mês anterior."))
        else:
            out.append(("📉", f"Gastos com {name} caíram {format_pct(abs(ch), 0)} vs. o mês anterior."))

    over = [b for b in budgets if b["status"] == "over"]
    if over:
        b = max(over, key=lambda x: x["usage"])
        out.append(("🔴", f"{b['category']} passou do orçamento ({format_pct(b['usage'], 0)} usado)."))
    else:
        under = [b for b in budgets if b["planned"] > 0 and b["usage"] < 80]
        if under:
            b = min(under, key=lambda x: x["usage"])
            out.append(("🟢", f"{b['category']} ficou {format_pct(100 - b['usage'], 0)} abaixo do orçamento."))

    tot = ctry.get("BR", 0) + ctry.get("JP", 0)
    if tot > 0:
        br = ctry.get("BR", 0) / tot * 100
        out.append(("🌎", f"Despesas: Brasil {format_pct(br, 0)} · Japão {format_pct(100 - br, 0)}."))

    for g, p in goals:
        icon = "🛟" if g["type"] == "emergency" else ("🏠" if g["type"] == "house" else "🎯")
        gc = p.get("currency", base)
        out.append((icon, f"{g['name']}: {format_pct(p['pct'], 0)} da meta "
                          f"({format_money(p['current'], gc)} de {format_money(p['target'], gc)})."))

    return out
