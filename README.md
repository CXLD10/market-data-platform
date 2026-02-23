# Market Data Platform

Stateless FastAPI market data gateway with in-memory caching and exchange abstraction.

## Scope
- No database usage.
- No historical persistence.
- In-memory TTL cache only.
- Yahoo Finance as primary provider.
- Unified output schemas for NSE, BSE, and NASDAQ.

## Reliability extensions
- Per-exchange circuit breaker (`CLOSED`, `OPEN`, `HALF_OPEN`).
- Controlled degradation (cached response or structured `EXCHANGE_UNAVAILABLE`).
- In-memory per-exchange request/latency/cache metrics.
- Exchange status and market session status endpoints.

## API
- `GET /quote?symbol=INFY&exchange=NSE`
- `GET /intraday?symbol=INFY&exchange=NSE&interval=5m`
- `GET /historical?symbol=INFY&exchange=NSE&period=6mo`
- `GET /fundamentals?symbol=INFY&exchange=NSE`
- `GET /company?symbol=INFY&exchange=NSE`
- `GET /search?query=INFY`
- `GET /metrics`
- `GET /exchanges/status`
- `GET /market-status?exchange=NSE`
- `GET /health`
- `GET /readiness`

Backward-compatible routes:
- `GET /candles`
- `GET /price/latest`
- `GET /symbols`

## Response versioning
All responses include:
- `schema_version: "1.1"`

## Local run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

## Tests
```bash
PYTHONPATH=. pytest -q
```
