# Market Data Platform

## System purpose
The Market Data Platform is a FastAPI service that provides a single authoritative HTTP interface for market prices and derived candles. It ingests trade events, stores time-series data in PostgreSQL, and exposes read APIs for downstream systems that require deterministic and queryable market data.

## Ownership boundaries
This service owns:
- symbol bootstrap and synthetic trade ingestion lifecycle
- persistence of symbols, trades, and candle aggregates
- HTTP contracts for market data reads
- runtime health and ingestion observability endpoints

This service does **not** own:
- portfolio logic
- model training logic
- strategy execution logic
- client-side caching policies in downstream systems

Consumers are expected to treat this service as the source of truth and avoid direct database coupling.

## What downstream systems should expect
Downstream systems (ML, analytics, portfolio, and research services) should expect:
- stable read-only HTTP APIs for latest, historical, and aggregated price data
- UTC timestamps and bounded query windows
- typed error payloads (`error`, `details`, `status`)
- ingestion freshness visibility via dedicated operational endpoints
- backward-compatible evolution of existing contracts

## Live deployment links
- Base URL: `https://market-data-platform-3qp7bblccq-uc.a.run.app`
- Swagger UI: `https://market-data-platform-3qp7bblccq-uc.a.run.app/docs`
- Health check: `https://market-data-platform-3qp7bblccq-uc.a.run.app/health`
- Redoc Page: `https://market-data-platform-3qp7bblccq-uc.a.run.app/redoc`

## Core API capabilities
- `GET /symbols` — list available symbols with pagination bounds
- `GET /price/latest?symbol=...` — latest trade snapshot per symbol
- `GET /trades?symbol=...&start=...&end=...&limit=...` — historical trade retrieval
- `GET /candles?symbol=...&interval=1m&start=...&end=...` — OHLCV aggregation view
- `GET /health` — service and database health
- `GET /status/ingestion` — heartbeat freshness and ingestion liveness
- `GET /metrics` — process uptime and request timing aggregates

## Operational features
- startup schema initialization (`create_all`) during service boot
- periodic ingestion loop with bounded retry behavior
- DB connection pooling with pre-ping health checks
- standardized request validation and structured error handling
- in-memory runtime telemetry for request latency and ingestion heartbeats
- process-safe container logging to stdout/stderr for Cloud Run

## Cloud deployment model
Production deployment is containerized and cloud-native:
- image built with `Dockerfile` and deployed to Cloud Run
- PostgreSQL hosted in Cloud SQL, connected through Unix socket (`DATABASE_URL`)
- CI/CD path defined through `cloudbuild.yaml` (build, push, deploy)
- environment-driven runtime configuration (`HOST`, `PORT`, ingestion interval, DB pool settings)
- stateless app instances; durable market data persisted in PostgreSQL

## Development philosophy
- API-first contracts for all inter-service integrations
- explicit validation at service boundaries
- incremental delivery in phases with compatibility preservation
- operational visibility treated as part of product completeness
- separation between ingestion concerns and read API concerns

## Service interoperability strategy
Interoperability is enforced through HTTP APIs rather than shared DB access:
- each downstream system integrates via documented endpoints
- contracts are centrally versioned in OpenAPI (`/docs`)
- symbol/time window conventions are normalized in one place
- platform-level governance can evolve APIs while preserving existing integrations

This approach reduces cross-team coupling and allows downstream services to scale independently.

## Project evolution (incremental maturity)
The platform evolved in explicit phases to improve reliability without breaking existing consumers.

### Phase 1 — minimal ingestion, persistence, and API
- introduced baseline symbol model, trade ingestion loop, and latest-price/health APIs
- established PostgreSQL as durable backing store and FastAPI as contract boundary

### Phase 2 — historical access and aggregation
- added bounded historical trades retrieval and OHLCV candle computation
- introduced interval and time-range validation to constrain query correctness

### Phase 3 — observability and health visibility
- added ingestion liveness status, freshness thresholds, and runtime metrics
- exposed operational endpoints to support production diagnostics

### Phase 4 — contract hardening and consumer readiness
- standardized error payloads and request validation semantics
- clarified pagination/limit controls and endpoint documentation for consumers

### Phase 5 — cloud-native deployment
- productionized deployment with Docker, Cloud Build, Cloud Run, and Cloud SQL
- ensured env-driven configuration and stateless runtime behavior for horizontal scaling

Each phase preserved backward compatibility for existing endpoints and improved the system’s operational confidence for integrators.

## Additional docs
- [Architecture](./architecture.md)
- [Local Quickstart](./quickstart.md)
