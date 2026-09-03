"""Leitura heurística de extratos/faturas em PDF (PDFs de TEXTO, não escaneados).

Cada banco usa um layout diferente, então isto é um "melhor esforço": procura, em
cada linha, uma DATA e um VALOR (formato brasileiro) e trata o resto como descrição.
O usuário sempre revisa numa prévia editável antes de gravar.
"""
import io
import re
from datetime import date

# dd/mm  ou  dd/mm/aa  ou  dd/mm/aaaa
_DATE_RE = re.compile(r"\b(\d{2}/\d{2}(?:/\d{2,4})?)\b")

# valor em real: 1.234,56 | 1234,56 | 12,00 | -12,00 | 12,00-  (R$ e sinais opcionais)
_MONEY_RE = re.compile(r"-?\s*R?\$?\s*(?:\d{1,3}(?:\.\d{3})+|\d+),\d{2}\s*-?")

# linhas de resumo que costumam ter data+valor mas NÃO são lançamentos
_SKIP_RE = re.compile(r"\bsaldo\b|\blimite\b|total\s+da\s+fatura|saldo\s+anterior", re.IGNORECASE)


def _to_float(tok: str):
    s = tok.strip()
    neg = s.startswith("-") or s.endswith("-")
    s = s.replace("R$", "").replace("$", "").replace(" ", "").strip("-")
    s = s.replace(".", "").replace(",", ".")
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


def _to_date(tok: str):
    parts = tok.split("/")
    try:
        d, m = int(parts[0]), int(parts[1])
        if len(parts) == 3:
            y = int(parts[2])
            if y < 100:
                y += 2000
        else:
            y = date.today().year
        return date(y, m, d)
    except Exception:
        return None


def extract_text(raw: bytes) -> str:
    """Texto bruto do PDF (todas as páginas). Requer pdfplumber."""
    import pdfplumber

    out = []
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        for page in pdf.pages:
            out.append(page.extract_text() or "")
    return "\n".join(out)


def extract_transactions(raw: bytes):
    """Retorna [{'date': date, 'desc': str, 'amount': float_com_sinal}] a partir do PDF."""
    return parse_text(extract_text(raw))


def parse_text(text: str):
    """Extrai lançamentos de um texto já lido (separado p/ facilitar testes)."""
    rows = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or _SKIP_RE.search(line):
            continue
        dm = _DATE_RE.search(line)
        if not dm:
            continue
        monies = _MONEY_RE.findall(line)
        if not monies:
            continue
        # 1 número = valor. 2+ números = ...valor, SALDO -> pega o penúltimo (ignora o saldo).
        amt = _to_float(monies[-2] if len(monies) >= 2 else monies[-1])
        d = _to_date(dm.group(1))
        if amt is None or d is None:
            continue
        # descrição = linha sem a data e sem os valores
        desc = (line[:dm.start()] + " " + line[dm.end():])
        desc = _MONEY_RE.sub(" ", desc)
        desc = re.sub(r"\s+", " ", desc).strip(" -•\t|")
        rows.append({"date": d, "desc": desc, "amount": amt})
    return rows
