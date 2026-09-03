"""Metas: progresso, aportes e simulações."""
from datetime import date

from src.db.client import get_client
from src.services.reference_service import load_context
from src.services.transaction_service import create_transaction
from src.utils import calculations as calc


def _client():
    return get_client()


def _num(x):
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def list_goals(active_only=True):
    q = _client().table("financial_goals").select("*").order("priority")
    if active_only:
        q = q.eq("is_active", True)
    return q.execute().data


def update_goal(goal_id, updates):
    return _client().table("financial_goals").update(updates).eq("id", goal_id).execute()


def create_goal(*, name, type="custom", target_amount=None, currency="BRL", monthly_plan=None, config=None):
    ctx = load_context()
    existing = list_goals(active_only=False)
    prio = max([g.get("priority", 0) for g in existing], default=0) + 1
    return _client().table("financial_goals").insert({
        "household_id": ctx["household_id"], "name": name, "type": type,
        "target_amount": target_amount, "currency": currency, "monthly_plan": monthly_plan,
        "config": config or {}, "priority": prio, "is_active": True,
    }).execute()


def deactivate_goal(goal_id):
    return _client().table("financial_goals").update({"is_active": False}).eq("id", goal_id).execute()


def contributions_total(goal_id):
    res = (_client().table("transactions").select("amount_base")
           .eq("type", "contribution").eq("goal_id", goal_id).execute().data)
    return sum(_num(r["amount_base"]) for r in res)


def _resolved_target(goal):
    config = goal.get("config") or {}
    gtype = goal["type"]
    if gtype == "emergency" and config.get("avg_monthly_expense") and config.get("months"):
        return calc.reserve_target(config["avg_monthly_expense"], config["months"])
    if gtype == "house" and config.get("property_value") and config.get("down_payment_pct"):
        return calc.house_target(config["property_value"], config["down_payment_pct"])
    return _num(goal.get("target_amount"))


def goal_progress(goal):
    current = contributions_total(goal["id"])
    config = goal.get("config") or {}
    target = _resolved_target(goal)
    remaining = calc.goal_remaining(target, current)
    monthly_plan = _num(goal.get("monthly_plan"))
    target_date = date.fromisoformat(goal["target_date"]) if goal.get("target_date") else None

    if target_date:
        months_left = calc.months_until(target_date)
        needed = calc.monthly_needed(remaining, months_left)
    else:
        months_left = calc.months_to_complete(remaining, monthly_plan)
        needed = monthly_plan

    out = {
        "current": current,
        "target": target,
        "remaining": remaining,
        "pct": calc.goal_pct(target, current),
        "monthly_plan": monthly_plan,
        "monthly_needed": needed,
        "months_left": months_left,
        "estimated_date": calc.estimated_date(remaining, monthly_plan) if monthly_plan else None,
        "currency": goal["currency"],
    }
    if goal["type"] == "emergency" and config.get("avg_monthly_expense"):
        out["months_covered"] = calc.months_covered(current, config["avg_monthly_expense"])
    return out


def add_contribution(goal, amount, member_id, currency=None, occurred_on=None, note=None):
    currency = currency or goal["currency"]
    country = "JP" if currency == "JPY" else "BR"
    return create_transaction(
        type="contribution", amount_original=amount, currency_original=currency,
        country=country, member_id=member_id, goal_id=goal["id"],
        description=f"Aporte · {goal['name']}", occurred_on=occurred_on, note=note,
    )


def simulate(goal, monthly_values):
    prog = goal_progress(goal)
    return [{"monthly": v, "date": calc.estimated_date(prog["remaining"], v)} for v in monthly_values]
