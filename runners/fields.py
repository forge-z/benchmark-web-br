"""Shared field parsing. The same rules for every tool."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone

PRICE_RE = re.compile(
    r"R\$\s*(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{2}))?",
    re.I,
)
CNPJ_RE = re.compile(r"\b(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})\b")
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?:\+55\s*)?(?:\(\d{2}\)|\d{2})\s*\d{4,5}[-\s]?\d{4}")

COMPANY_FIELDS = [
    "cnpj",
    "razao_social",
    "cidade",
    "uf",
    "porte",
    "segmento",
    "site",
    "linkedin_empresa",
    "cargo_decisor_comercial",
    "noticia_recente",
]


def fold(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.upper()
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def cnpj_digits(value: str) -> str:
    found = CNPJ_RE.search(value or "")
    raw = digits(found.group(1) if found else value or "")
    return raw if len(raw) == 14 else ""


def cnpj_valid(value: str) -> bool:
    raw = cnpj_digits(value)
    if len(raw) != 14 or len(set(raw)) == 1:
        return False
    def calc(base: str, weights: list[int]) -> str:
        rest = sum(int(a) * b for a, b in zip(base, weights)) % 11
        return "0" if rest < 2 else str(11 - rest)
    first = calc(raw[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    second = calc(raw[:12] + first, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return raw[-2:] == first + second


def format_cnpj(value: str) -> str:
    raw = cnpj_digits(value)
    if len(raw) != 14:
        return ""
    return f"{raw[:2]}.{raw[2:5]}.{raw[5:8]}/{raw[8:12]}-{raw[12:]}"


def canonical_price(value: str) -> str:
    """Brazilian reais: R$ 1.234,56. Empty when no amount is found."""
    match = PRICE_RE.search(value or "")
    if not match:
        return ""
    whole = match.group(1).replace(".", "")
    cents = match.group(2) or "00"
    number = int(whole)
    body = f"{number:,}".replace(",", ".")
    return f"R$ {body},{cents}"


def parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    for candidate in (text, text.replace(" ", "T")):
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(value.strip(), fmt).astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def to_iso(value: str) -> str:
    parsed = parse_datetime(value)
    if parsed is None:
        return ""
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def host_of(url: str) -> str:
    match = re.search(r"https?://([^/?#]+)", (url or "").lower())
    if not match:
        return ""
    host = match.group(1)
    return host[4:] if host.startswith("www.") else host


def empty_answers() -> dict:
    return {field: {"value": "", "citations": []} for field in COMPANY_FIELDS}


def empty_page(url: str = "") -> dict:
    return {
        "url": url,
        "title": "",
        "text": "",
        "published_at": "",
        "price_brl": "",
        "seller": "",
        "availability": "",
        "blocked": False,
    }


def news_item(url: str = "", title: str = "", published_at: str = "", snippet: str = "") -> dict:
    return {
        "url": url or "",
        "title": title or "",
        "published_at": to_iso(published_at) or (published_at or ""),
        "snippet": (snippet or "")[:500],
    }


def contains_contact(value: str) -> bool:
    return bool(EMAIL_RE.search(value or "") or PHONE_RE.search(value or ""))


def linkedin_company_url(value: str) -> str:
    match = re.search(r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/company/[A-Za-z0-9_%.-]+/?", value or "", re.I)
    if not match:
        return ""
    return match.group(0).rstrip("/")
