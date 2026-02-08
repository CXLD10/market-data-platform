# Market Data Platform - Phase 3

A production-oriented time-series service that acts as the authoritative source of financial price information for a broader fintech ecosystem.

## Overview

This is **Phase 3**. The platform now provides:
- Continuous synthetic trade ingestion
- Historical trade queries
- On-demand historical candle generation
- Runtime observability endpoints for freshness and operational health
- A lightweight auto-refresh dashboard for operators

## Quick Start

### Prerequisites
- Docker and Docker Compose
- curl (and optionally `jq`)

### Run the Platform

```bash
docker compose up -d --build
```

The service will automatically:
1. Start PostgreSQL
2. Initialize schema
3. Start background ingestion (default every 3s)
4. Expose HTTP APIs on `http://localhost:8000`

### Smoke Test

```bash
./test_api.sh
```

## API Endpoints

### Core Data APIs
- `GET /health`
- `GET /symbols`
- `GET /price/latest?symbol=AAPL`
- `GET /trades?symbol=AAPL&start=<ISO8601>&end=<ISO8601>&limit=100`
- `GET /candles?symbol=AAPL&interval=1m&start=<ISO8601>&end=<ISO8601>`

### Observability APIs (Phase 3)
- `GET /metrics`
- `GET /status/ingestion`
- `GET /dashboard` (simple HTML page)

## Freshness and Operational Visibility

### How freshness is determined
- Ingestion heartbeat is updated after each successful write batch.
- `GET /status/ingestion` reports `ingestion_alive` and `ingestion_status`.
- Ingestion is considered **alive** if heartbeat age is within:

```text
INGESTION_INTERVAL_SECONDS * 3
```

- If heartbeat age exceeds this threshold (or no heartbeat yet), ingestion is **dead/stale**.

### What downstream services should do when stale
If `ingestion_alive=false`:
1. Mark market data as stale in your service state.
2. Stop making trading/risk decisions that require fresh ticks.
3. Fall back to cached last-known-good data with explicit stale metadata.
4. Trigger alerting and/or incident workflows.
5. Continue polling `/status/ingestion` until recovery.

If DB health is false (`db_healthy=false` / `db.healthy=false`):
- Treat responses as degraded and avoid assuming counts/freshness are reliable.
- Retry with backoff and alert operators.

## Dashboard Behavior

The dashboard at `/dashboard` is intentionally simple and auto-refreshes every 5 seconds.

It displays:
- Ingestion alive/dead
- Seconds since last trade
- Total trades
- Total candles
- DB healthy
- Service uptime

**Critical rule:** the dashboard reads observability only via HTTP APIs (`/metrics`, `/status/ingestion`) and does not query the database directly.

## Configuration

Environment variables:
- `DATABASE_URL`
- `LOG_LEVEL`
- `INGESTION_INTERVAL_SECONDS`

See `docker-compose.yml` for local defaults.

## Interactive Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```text
market-data-platform/
├── app/
│   ├── api.py
│   ├── ingestion.py
│   ├── observability.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── config.py
│   └── main.py
├── docker-compose.yml
├── Dockerfile
├── test_api.sh
├── QUICK_START.md
├── ARCHITECTURE.md
└── IMPLEMENTATION_SUMMARY.md
```
