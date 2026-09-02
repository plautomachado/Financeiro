"""Regras de categorização automática (descrição contém X → categoria Y)."""
import unicodedata

from src.db.client import get_client
from src.services.reference_service import load_context


def _client():
    return get_client()


def _strip(s):
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def list_rules(active_only=True):
    q = _client().table("categorization_rules").select("*").order("priority").order("created_at")
    if active_only:
        q = q.eq("is_active", True)
    return q.execute().data


def create_rule(match_text, category_id, member_id=None, priority=0):
    ctx = load_context()
    return _client().table("categorization_rules").insert({
        "household_id": ctx["household_id"], "match_text": match_text, "category_id": category_id,
        "member_id": member_id, "priority": priority, "is_active": True,
    }).execute()


def delete_rule(rule_id):
    return _client().table("categorization_rules").delete().eq("id", rule_id).execute()


def categorize(description, rules=None):
    """Retorna (category_id, member_id) da 1ª regra que casar; senão (None, None)."""
    if rules is None:
        rules = list_rules()
    d = _strip(description)
    for r in rules:
        mt = _strip(r.get("match_text"))
        if mt and mt in d:
            return r.get("category_id"), r.get("member_id")
    return None, None
