"""Regras de categorização automática (descrição contém X → categoria Y).

Casamento "inteligente": ignora acentos/pontuação, casa por palavra-chave
(a regra "Mandai loja Sakai" ainda pega "Mandai Sakaihaze") e, se nenhuma regra
casar, tenta reconhecer o próprio nome da categoria dentro da descrição.
"""
import re
import unicodedata

from src.db.client import get_client
from src.services.reference_service import load_context


def _client():
    return get_client()


def _strip(s):
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def _norm(s):
    """Sem acento, minúsculo, pontuação/símbolo viram espaço."""
    s = _strip(s)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s)).strip()


def _rule_score(match_text, d):
    """Quão bem a regra casa com a descrição normalizada `d`. 0 = não casa."""
    mt = _norm(match_text)
    if not mt:
        return 0
    if mt in d:                                  # casa direto (mais forte)
        return 1000 + len(mt)
    words = [w for w in mt.split() if len(w) >= 3]
    if not words:
        return 0
    matched = [w for w in words if w in d]       # palavras da regra presentes
    if not matched:
        return 0
    first_ok = words[0] in d                      # a 1ª palavra (comércio) casou?
    if first_ok or len(matched) / len(words) >= 0.6:
        return len(matched) * 10 + (20 if first_ok else 0)
    return 0


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


def categorize(description, rules=None, categories=None):
    """Retorna (category_id, member_id) pela MELHOR regra; se nenhuma casar, tenta
    reconhecer o nome de uma categoria na descrição. Senão (None, None)."""
    if rules is None:
        rules = list_rules()
    d = _norm(description)
    if not d:
        return None, None

    # 1) melhor regra (casamento flexível por palavra-chave)
    best, best_score = None, 0
    for r in rules:
        sc = _rule_score(r.get("match_text"), d)
        if sc > best_score:
            best, best_score = r, sc
    if best:
        return best.get("category_id"), best.get("member_id")

    # 2) fallback: o nome da categoria aparece na descrição? (ex.: "...restaurante" -> Restaurantes)
    if categories is None:
        try:
            categories = load_context().get("categories", [])
        except Exception:
            categories = []
    d_words = set(d.split())
    for c in categories:
        for w in _norm(c.get("name", "")).split():
            if len(w) < 4:
                continue
            if w in d_words or w.rstrip("s") in d_words or (w + "s") in d_words:
                return c.get("id"), None
    return None, None
