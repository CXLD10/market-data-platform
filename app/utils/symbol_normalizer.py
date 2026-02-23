import re

from app.utils.exchange_mapper import Exchange

_SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,16}$")


def normalize_symbol(symbol: str) -> str:
    cleaned = symbol.strip().upper()
    if not cleaned or not _SYMBOL_PATTERN.match(cleaned):
        raise ValueError("invalid symbol")
    return cleaned


def normalize_exchange(exchange: str) -> Exchange:
    try:
        return Exchange(exchange.strip().upper())
    except Exception as exc:
        raise ValueError("invalid exchange") from exc
