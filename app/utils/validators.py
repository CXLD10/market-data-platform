from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def to_native_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        casted = float(value)
        if casted != casted:
            return default
        return casted
    except (TypeError, ValueError):
        return default


def to_native_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        iso = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_valid_price(price: float) -> bool:
    return price >= 0


def sanitize_candles(candles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    prev_close: float | None = None

    for candle in candles:
        if candle.get("volume", 0) <= 0:
            continue
        if min(candle.get("open", -1), candle.get("high", -1), candle.get("low", -1), candle.get("close", -1)) < 0:
            continue

        close = float(candle["close"])
        if prev_close and prev_close > 0:
            jump = abs(close - prev_close) / prev_close
            if jump > 0.5:
                continue

        ts = normalize_timestamp(candle["timestamp"]).isoformat()
        candle["timestamp"] = ts
        cleaned.append(candle)
        prev_close = close

    cleaned.sort(key=lambda item: item["timestamp"])
    return cleaned
