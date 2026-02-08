# Architecture - Phase 3

## System Summary

Market Data Platform is an independent service that:
1. Ingests synthetic trade data continuously
2. Persists canonical records in PostgreSQL
3. Serves stable HTTP APIs for downstream systems
4. Exposes runtime observability and a simple operator dashboard

## High-Level Components

- **FastAPI application** (`app/api.py`, `app/main.py`)
- **Ingestion loop** (`app/ingestion.py`)
- **Relational storage** (PostgreSQL via SQLAlchemy)
- **Observability runtime state** (`app/observability.py`)
- **Dashboard UI** (server-rendered HTML at `/dashboard`)

## Data Model

### `symbols`
List of supported symbols (AAPL, GOOGL, MSFT, TSLA, AMZN).

### `trades`
Raw trade events with timestamp, symbol, price, and volume.

### `candles`
OHLCV aggregations by symbol, interval, and bucket timestamp.

## Request/Processing Flows

### Ingestion flow
1. Startup initializes symbols.
2. Every `INGESTION_INTERVAL_SECONDS`, service generates trades.
3. Writes are committed as a batch transaction.
4. On successful commit, ingestion heartbeat is updated.

### Historical candle flow
1. Client requests `/candles` for range + interval.
2. Service scans matching trades, computes OHLCV buckets.
3. Upserts candle rows and returns ordered candle response.

### Observability flow
- Middleware measures API request latency.
- `/metrics` returns:
  - counts (trades/candles)
  - API latency aggregates
  - DB health
  - uptime/start time
  - ingestion freshness stats
- `/status/ingestion` returns:
  - alive/dead status
  - heartbeat age
  - seconds since last trade
  - DB health
  - uptime/start time

## Freshness Model

- Heartbeat = last successful ingestion write.
- Stale threshold = `INGESTION_INTERVAL_SECONDS * 3`.
- If heartbeat age exceeds threshold, ingestion is marked dead/stale.

This model is intentionally conservative and easy for downstream consumers to reason about.

## Dashboard Constraints

`/dashboard` **must act as an external client**:
- It fetches `/metrics` and `/status/ingestion` via HTTP.
- It does not read the DB directly.

This ensures operational UI behavior matches real downstream integrations.

## Reliability Properties

- API contracts are additive and stable.
- DB pool pre-ping helps avoid stale connections.
- Ingestion loop recovers from transient errors and keeps running.
- Health and status endpoints provide quick service diagnostics.

## Deployment Model

- Docker Compose for local deployment:
  - `postgres` service
  - `api` service
- `api` starts with `python -m app.main`
- Environment-driven configuration (12-factor style)
