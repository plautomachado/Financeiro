"""Formatação de moeda e percentuais no padrão pt-BR (sem depender de locale)."""

CURRENCY_SYMBOLS = {"BRL": "R$", "JPY": "¥", "EUR": "€", "USD": "$"}
CURRENCY_DECIMALS = {"BRL": 2, "JPY": 0, "EUR": 2, "USD": 2}
COUNTRY_NAMES = {"BR": "Brasil", "JP": "Japão", "EU": "Europa", "US": "EUA"}


def format_money(value, currency="BRL", with_symbol=True):
    if value is None:
        value = 0
    decimals = CURRENCY_DECIMALS.get(currency, 2)
    s = f"{float(value):,.{decimals}f}"          # 1,234.56 (padrão en)
    s = s.replace(",", "§").replace(".", ",").replace("§", ".")  # -> 1.234,56 (pt-BR)
    if with_symbol:
        return f"{CURRENCY_SYMBOLS.get(currency, '')} {s}".strip()
    return s


def format_pct(value, decimals=1):
    if value is None:
        return "—"
    s = f"{float(value):.{decimals}f}".replace(".", ",")
    return f"{s}%"
