# Quick Start

## Prerequisites

- Python 3.11+
- pip

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

Service default URL: `http://localhost:8000`

## Smoke test endpoints

```bash
curl "http://localhost:8000/health"
curl "http://localhost:8000/quote?symbol=INFY&exchange=NSE"
curl "http://localhost:8000/search?query=INFY"
curl "http://localhost:8000/metrics"
```

## Run tests

```bash
PYTHONPATH=. pytest -q
```

## Docker local run

```bash
docker build -t market-data-gateway:local .
docker run --rm -p 8000:8000 market-data-gateway:local
```

## Cloud Run deploy (manual)

```bash
PROJECT_ID=<your-project>
REGION=us-central1
SERVICE=market-data-gateway
REPO=market-data
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/$SERVICE:latest"

gcloud builds submit --tag "$IMAGE"

gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated
```
