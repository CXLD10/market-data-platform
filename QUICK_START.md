# Quick Start - Phase 3

Get the Market Data Platform running locally with observability and dashboard support.

## 1) Start the services

```bash
docker compose up -d --build
```

## 2) Verify containers

```bash
docker compose ps
docker compose logs -f api
```

## 3) Validate core APIs

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
curl -s http://localhost:8000/symbols | python3 -m json.tool
curl -s "http://localhost:8000/price/latest?symbol=AAPL" | python3 -m json.tool
```

## 4) Validate historical APIs

```bash
END_TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
START_TS=$(date -u -d '10 minutes ago' +"%Y-%m-%dT%H:%M:%SZ")

curl -s "http://localhost:8000/trades?symbol=AAPL&start=${START_TS}&end=${END_TS}&limit=100" | python3 -m json.tool
curl -s "http://localhost:8000/candles?symbol=AAPL&interval=1m&start=${START_TS}&end=${END_TS}" | python3 -m json.tool
```

## 5) Validate Phase 3 observability APIs

```bash
curl -s http://localhost:8000/metrics | python3 -m json.tool
curl -s http://localhost:8000/status/ingestion | python3 -m json.tool
```

## 6) Open dashboard

Visit:

```text
http://localhost:8000/dashboard
```

If you are in a non-GUI shell/VM/container, use curl:

```bash
curl -s http://localhost:8000/dashboard | head -n 40
```

## 7) Run bundled smoke test

```bash
chmod +x test_api.sh
./test_api.sh
```

## Troubleshooting

### `/metrics` or `/status/ingestion` returns 404
You are likely running an old image.

```bash
docker compose down
docker compose up -d --build --force-recreate
```

### Browser open command fails (e.g., xdg-open/open)
No desktop browser is installed in your environment. Use curl checks or open URL from your local machine.

### Freshness appears stale
Check ingestion logs:

```bash
docker compose logs -f api
```

You should see periodic `Generated X trades` messages.
