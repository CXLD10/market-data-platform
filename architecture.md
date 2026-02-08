# Architecture — Market Data Platform

## 1. Overview
Market Data Platform is a single-service data system with a clear separation between write path (ingestion) and read path (HTTP query APIs). PostgreSQL is the durable system of record, while FastAPI exposes stable contracts for all consumers.

## 2. Ingestion pipeline
1. Service startup initializes DB schema.
2. Ingestion service ensures default symbols exist.
3. A timed loop generates trades per symbol using a bounded random walk.
4. Trades are written to PostgreSQL in timestamped batches.
5. Successful writes update ingestion heartbeat telemetry.

Characteristics:
- ingestion interval is configurable (`INGESTION_INTERVAL_SECONDS`)
- ingestion failures are logged and retried in the next cycle
- ingestion continues independently of read request volume

## 3. Storage model
Primary relational entities:
- `symbols` — symbol metadata and identity key
- `trades` — raw time-series events (`symbol`, `price`, `volume`, `timestamp`)
- `candles` — derived OHLCV aggregates by (`symbol`, `interval`, `timestamp`)

Indexing strategy emphasizes symbol + time access patterns:
- trades indexed by `(symbol, timestamp)`
- candles indexed by `(symbol, timestamp)`
- unique candle constraint on `(symbol, interval, timestamp)`

Implication: historical and candle queries remain predictable for common analytical windows.

## 4. Candle aggregation model
Candle generation is performed on-demand in the API layer:
- query-range trades are scanned once in ascending time
- data is bucketed into aligned interval boundaries
- OHLCV + trade count are computed per bucket
- computed candles are upserted into `candles`
- response is served from persisted candle rows

Rationale:
- keeps ingestion path simple and resilient
- isolates aggregate logic from raw trade generation
- enables deterministic recomputation for requested windows

Current supported interval set is intentionally constrained (`1m`) to maintain contract simplicity.

## 5. API layer
FastAPI provides read-only contracts for downstream systems:
- discovery/root: `/`
- health and operations: `/health`, `/status/ingestion`, `/metrics`
- market data: `/symbols`, `/price/latest`, `/trades`, `/candles`
- documentation: `/docs` (Swagger), `/redoc`

API boundary behavior:
- strict query validation (symbol format, time ordering, limits)
- UTC handling for timestamps
- standardized error envelope for predictable client handling

## 6. Observability model
Observability combines DB checks and process-level signals:
- DB connectivity probes in health/metrics endpoints
- ingestion heartbeat timestamp and staleness window (`3 x ingestion interval`)
- request latency aggregates (count, average, max, last)
- process uptime and startup timestamp

Scope note: runtime telemetry is in-memory and therefore instance-local by design.

## 7. Deployment topology
Production target is Google Cloud Run:
- container image built from repository Dockerfile
- service deployed as stateless Cloud Run revision(s)
- persistence externalized to Cloud SQL PostgreSQL
- Cloud Build pipeline (`cloudbuild.yaml`) handles build/push/deploy stages

Connectivity pattern:
- app receives `DATABASE_URL`
- Cloud SQL access uses Unix socket host (`/cloudsql/<instance-connection-name>`)
- app binds to Cloud Run-provided `PORT`

## 8. Dependency direction
Dependency flow is intentionally one-directional:
- `ingestion` and `api` depend on `database`, `models`, `config`, `observability`
- no downstream system depends on internal DB schema directly
- external consumers depend only on HTTP contracts

This prevents reverse coupling from consumer teams into service internals.

## 9. Failure implications
- **DB unavailable**: health degrades; read endpoints and ingestion fail until connectivity returns.
- **Ingestion loop exception**: loop logs error and retries next interval; data freshness may degrade temporarily.
- **API instance restart**: in-memory metrics reset on that instance; durable trade/candle history remains intact.
- **Consumer misuse (invalid ranges/symbols)**: request rejected with structured validation/client errors.

Operationally, the highest-risk dependency is PostgreSQL availability and latency.

## 10. Why API-based access is enforced
API-only access is deliberate for governance and reliability:
- central validation and normalization of market data semantics
- stable contracts independent of storage refactors
- consistent authorization, auditing, and observability points
- reduced blast radius from schema changes
- cleaner cross-team boundaries for ML and analytics integrators

Direct database access by downstream services is intentionally excluded from the operating model.
