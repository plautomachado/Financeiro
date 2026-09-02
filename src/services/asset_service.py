"""Patrimônio: ativos (contas/investimentos) + consolidação e snapshots mensais."""
from datetime import datetime, timezone

from src.db.client import get_client
from src.services.reference_service import load_context, latest_rate

TYPE_LABELS = {
    "available": "Disponível",
    "reserve": "Reserva",
    "house": "Entrada da casa",
    "investment": "Investimentos",
    "other": "Outros",
}
TYPE_ORDER = ["available", "reserve", "house", "investment", "other"]


def _client():
    return get_client()


def to_base(value, currency, base):
    if currency == base:
        return float(value or 0)
    return float(value or 0) * (latest_rate(currency, base) or 1)


def list_assets(active_only=True):
    q = _client().table("assets").select("*").order("name")
    if active_only:
        q = q.eq("is_active", True)
    return q.execute().data


def create_asset(*, name, type, country, currency, current_value, member_id=None, note=None):
    ctx = load_context()
    return _client().table("assets").insert({
        "household_id": ctx["household_id"], "name": name, "type": type, "country": country,
        "currency": currency, "current_value": float(current_value), "member_id": member_id,
        "note": note, "is_active": True,
    }).execute()


def update_asset_value(asset_id, current_value):
    return _client().table("assets").update({
        "current_value": float(current_value),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", asset_id).execute()


def deactivate_asset(asset_id):
    return _client().table("assets").update({"is_active": False}).eq("id", asset_id).execute()


def net_worth():
    ctx = load_context()
    base = ctx["base_currency"]
    assets = list_assets()
    by_country = {"BR": 0.0, "JP": 0.0, "EU": 0.0, "US": 0.0}
    by_type = {k: 0.0 for k in TYPE_LABELS}
    total = 0.0
    for a in assets:
        v = to_base(a["current_value"], a["currency"], base)
        total += v
        by_country[a["country"]] = by_country.get(a["country"], 0) + v
        by_type[a["type"]] = by_type.get(a["type"], 0) + v
    return {"total": total, "by_country": by_country, "by_type": by_type, "base": base, "assets": assets}


def save_snapshot(year, month):
    ctx = load_context()
    nw = net_worth()
    return _client().table("monthly_snapshots").upsert({
        "household_id": ctx["household_id"], "year": year, "month": month,
        "net_worth_base": round(nw["total"], 2),
        "br_base": round(nw["by_country"].get("BR", 0), 2),
        "jp_base": round(nw["by_country"].get("JP", 0), 2),
        "base_currency": nw["base"],
    }, on_conflict="household_id,year,month").execute()


def list_snapshots():
    return (_client().table("monthly_snapshots").select("*")
            .order("year").order("month").execute().data)
