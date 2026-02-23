from __future__ import annotations

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from app.utils.exchange_mapper import Exchange


_EXCHANGE_RULES = {
    Exchange.NSE: {"tz": "Asia/Kolkata", "open": time(9, 15), "close": time(15, 30)},
    Exchange.BSE: {"tz": "Asia/Kolkata", "open": time(9, 15), "close": time(15, 30)},
    Exchange.NASDAQ: {"tz": "America/New_York", "open": time(9, 30), "close": time(16, 0)},
}


def get_market_status(exchange: Exchange) -> dict[str, str | bool]:
    rule = _EXCHANGE_RULES[exchange]
    now_utc = datetime.now(timezone.utc)
    local_tz = ZoneInfo(rule["tz"])
    local_now = now_utc.astimezone(local_tz)

    is_weekday = local_now.weekday() < 5
    is_open = is_weekday and (rule["open"] <= local_now.time().replace(tzinfo=None) <= rule["close"])

    return {
        "exchange": exchange.value,
        "is_open": is_open,
        "session": "REGULAR" if is_open else "CLOSED",
        "timezone": rule["tz"],
        "server_time_utc": now_utc.isoformat(),
        "local_exchange_time": local_now.isoformat(),
    }
