"""Interpretação de lançamentos por texto (linguagem natural).

Ex.: "mercado 3850"  ·  "esposa mercado 185 reais"  ·  "uber 1200 ontem"
Devolve um dict com os campos entendidos + avisos; a página sempre confirma antes de gravar.
"""
import re
import unicodedata
from datetime import date, timedelta


def _strip(s):
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


CURRENCY_WORDS = {
    "r$": "BRL", "brl": "BRL", "reais": "BRL", "real": "BRL",
    "¥": "JPY", "jpy": "JPY", "iene": "JPY", "ienes": "JPY", "yen": "JPY", "iens": "JPY",
    "€": "EUR", "eur": "EUR", "euro": "EUR", "euros": "EUR",
    "usd": "USD", "dolar": "USD", "dolares": "USD",
}

TYPE_WORDS = {
    "income": ["recebi", "salario", "receita", "ganhei", "entrou", "recebemos"],
    "contribution": ["aporte", "aportei", "aportamos", "guardei", "poupei", "investi", "reserva"],
}

CATEGORY_SYNONYMS = {
    "Mercado": ["mercado", "supermercado", "feira", "mandai", "aeon", "gyomu"],
    "Restaurantes": ["restaurante", "almoco", "jantar", "lanche", "cafe", "ifood", "izakaya", "sushi"],
    "Transporte": ["transporte", "uber", "taxi", "trem", "onibus", "metro", "gasolina", "combustivel", "pedagio"],
    "Moradia": ["aluguel", "moradia", "condominio", "iptu"],
    "Saude": ["saude", "farmacia", "remedio", "medico", "hospital", "dentista"],
    "Educacao": ["educacao", "escola", "curso", "faculdade", "livro"],
    "Lazer": ["lazer", "cinema", "jogo", "game", "parque", "bar"],
    "Telefone": ["telefone", "celular", "recarga"],
    "Internet": ["internet", "wifi", "banda larga"],
    "Energia": ["energia", "luz", "eletricidade"],
    "Agua": ["agua"],
    "Roupas": ["roupa", "roupas", "tenis", "sapato"],
    "Assinaturas": ["netflix", "spotify", "assinatura", "youtube", "prime", "disney"],
    "Carro": ["carro", "oficina", "mecanico", "estacionamento"],
}


def _parse_amount(low):
    tokens = re.findall(r"\d[\d.,]*", low)
    if not tokens:
        return None
    tok = max(tokens, key=len)
    if "," in tok:                                    # 185,90 / 1.234,56
        tok = tok.replace(".", "").replace(",", ".")
    elif tok.count(".") == 1 and len(tok.split(".")[1]) == 3:
        tok = tok.replace(".", "")                    # 3.850 -> 3850
    try:
        return round(float(tok), 2)
    except ValueError:
        return None


def parse_entry(text, members, categories, base_currency="BRL", cards=None):
    raw = (text or "").strip()
    low = _strip(raw)
    warnings = []
    res = {"raw": raw}

    # parcelas: "5 parcelas", "5x", "5 vezes"
    parcelas = 1
    mp = re.search(r"(\d+)\s*(?:x|parcelas?|vezes|vzs)\b", low)
    if mp:
        parcelas = int(mp.group(1))
    res["parcelas"] = parcelas

    # cartão (casa por nome) — guardado para não confundir o número do cartão com o valor
    card = None
    low_amt = low
    if cards:
        for c in cards:
            nm = _strip(c.get("name"))
            if nm and nm in low:
                card = c
                low_amt = low_amt.replace(nm, " ")
                break
    res["card"] = card
    res["is_credit"] = any(w in low for w in ("credito", "cartao"))

    # valor (remove o trecho de parcelas; entende "mil" = x1000)
    low_amt = re.sub(r"\d+\s*(?:x|parcelas?|vezes|vzs)\b", " ", low_amt)
    amount = _parse_amount(low_amt)
    if amount is not None and re.search(r"\bmil\b", low_amt):
        amount *= 1000
    if amount is None:
        warnings.append("Não encontrei o valor.")
    res["amount"] = amount

    # tipo
    ttype = "expense"
    for t, words in TYPE_WORDS.items():
        if any(w in low for w in words):
            ttype = t
            break
    res["type"] = ttype

    # pessoa
    member = None
    for m in members:
        if _strip(m["name"]) in low:
            member = m
            break
    if member is None and members:
        member = members[0]
        warnings.append(f"Pessoa não citada — assumi {member['name']}.")
    res["member"] = member

    # moeda
    currency = None
    for w, cur in CURRENCY_WORDS.items():
        if w in low:
            currency = cur
            break
    if currency is None:
        currency = member["default_currency"] if member else base_currency
    res["currency"] = currency

    # país (a partir da moeda; senão do padrão da pessoa)
    country = {"BRL": "BR", "JPY": "JP", "EUR": "EU", "USD": "US"}.get(currency)
    if country is None:
        country = member["default_country"] if member else "BR"
    res["country"] = country

    # categoria (para despesa/receita)
    category = None
    if ttype in ("expense", "income"):
        stripped = {_strip(c["name"]): c for c in categories}
        for sname, c in stripped.items():
            if sname and sname in low:
                category = c
                break
        if category is None:
            for canon, syns in CATEGORY_SYNONYMS.items():
                if any(s in low for s in syns):
                    key = _strip(canon)
                    if key in stripped:
                        category = stripped[key]
                    break
        if category is None and ttype == "expense":
            warnings.append("Categoria não identificada — ajuste se precisar.")
    res["category"] = category

    # data
    d = date.today()
    if "ontem" in low:
        d = date.today() - timedelta(days=1)
    res["date"] = d

    res["warnings"] = warnings
    return res
