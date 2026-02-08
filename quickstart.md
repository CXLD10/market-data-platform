# Quickstart (Local Development)

## 1) Prerequisites
- Docker + Docker Compose plugin
- `curl`
- optional: `python3` for JSON pretty-printing

## 2) Environment configuration
Create a local `.env` file (or copy from `.env.example`):

```bash
cp .env.example .env
```

If needed, update values:

```dotenv
DATABASE_URL=postgresql://marketdata:localdev123@localhost:5432/market_data
LOG_LEVEL=INFO
INGESTION_INTERVAL_SECONDS=3
```

> When running with the provided `docker-compose.yml`, the API container receives its own internal `DATABASE_URL` (`postgres` hostname in Docker network). The `.env` file is mainly useful for non-compose local execution.

## 3) Start services with Docker Compose
```bash
docker compose up -d --build
```

Validate status:

```bash
docker compose ps
docker compose logs -f api
```

## 4) Access API and docs
- API base: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health: `http://localhost:8000/health`

## 5) Example API usage (curl)
### Health and operational checks
```bash
curl -s http://localhost:8000/health | python3 -m json.tool
curl -s http://localhost:8000/status/ingestion | python3 -m json.tool
curl -s http://localhost:8000/metrics | python3 -m json.tool
```

### Data access
```bash
curl -s http://localhost:8000/symbols | python3 -m json.tool
curl -s "http://localhost:8000/price/latest?symbol=AAPL" | python3 -m json.tool
```

### Historical window + candles
```bash
END_TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
START_TS=$(date -u -d '15 minutes ago' +"%Y-%m-%dT%H:%M:%SZ")

curl -s "http://localhost:8000/trades?symbol=AAPL&start=${START_TS}&end=${END_TS}&limit=100" | python3 -m json.tool
curl -s "http://localhost:8000/candles?symbol=AAPL&interval=1m&start=${START_TS}&end=${END_TS}" | python3 -m json.tool
```

## 6) Stop local stack
```bash
docker compose down
```

To also remove persisted local PostgreSQL data:

```bash
docker compose down -v
```

## 7) Common issues
- **No data yet**: wait one or two ingestion intervals, then retry `/price/latest`.
- **Connection refused on `localhost:8000`**: verify `api` container is running (`docker compose ps`).
- **Stale ingestion status**: inspect API logs (`docker compose logs -f api`) for ingestion loop errors.
