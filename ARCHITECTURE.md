# Architecture

## Overview

Market Data Gateway is a stateless FastAPI service that fetches market data on demand from Yahoo Finance, normalizes responses, and serves exchange-neutral APIs.

## Design constraints

- No database
- No historical persistence
- No Redis or external cache
- In-memory TTL caching only
- Deterministic response contracts

## Runtime modules

- `app/api/routes.py` - HTTP routes, middleware, degradation behavior
- `app/exchanges/yahoo_adapter.py` - provider adapter and normalization input layer
- `app/services/*` - use-case services (quote, intraday, historical, fundamentals, search)
- `app/cache/ttl_cache.py` - in-memory TTL cache with hit/miss metrics
- `app/resilience_circuit_breaker.py` - per-exchange circuit management
- `app/internal_metrics.py` - in-memory operational metrics
- `app/utils/*` - symbol/exchange normalization, validation, market hours logic
- `app/schemas/*` - strict response schemas

## Resilience flow

1. Request enters route.
2. Exchange and symbol are validated.
3. Circuit state checked per exchange.
4. If OPEN: return cache fallback if present, otherwise structured error.
5. If execution allowed: fetch via adapter/service.
6. Validate and normalize output.
7. Record success/failure and metrics.

## Observability

- `/metrics` returns process-level request/cache/latency summary.
- `/exchanges/status` returns per-exchange state and failure/latency indicators.
- `/market-status` returns deterministic exchange session status from static trading-hour rules.

## Deployment model

- Containerized and Cloud Run deployable
- Non-root runtime user
- Environment-driven settings
- Horizontal scale with instance-local in-memory state

