from enum import Enum


class Exchange(str, Enum):
    NSE = "NSE"
    BSE = "BSE"
    NASDAQ = "NASDAQ"


_SUFFIX_MAP = {
    Exchange.NSE: ".NS",
    Exchange.BSE: ".BO",
    Exchange.NASDAQ: "",
}


def to_provider_symbol(symbol: str, exchange: Exchange) -> str:
    suffix = _SUFFIX_MAP[exchange]
    return f"{symbol.upper()}{suffix}"


def from_provider_symbol(provider_symbol: str) -> tuple[str, Exchange]:
    upper = provider_symbol.upper()
    if upper.endswith(".NS"):
        return upper[:-3], Exchange.NSE
    if upper.endswith(".BO"):
        return upper[:-3], Exchange.BSE
    return upper, Exchange.NASDAQ
