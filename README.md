# Market Data Platform

A production-oriented time-series service that acts as the authoritative source of financial price information.

## Cloud-native runtime behavior

This service is designed to run unchanged in both local Docker and Cloud Run:
- Binds to `HOST` / `PORT` (Cloud Run injects `PORT`).
- Uses only `DATABASE_URL` for PostgreSQL connectivity.
- Supports Cloud SQL Unix socket URLs (for example: `postgresql://USER:PASSWORD@/DB?host=/cloudsql/INSTANCE`).
- Logs to stdout/stderr.
- Treats filesystem as ephemeral (no local persistence required).
- Supports clean startup/shutdown via FastAPI lifespan hooks.

## Quick start (local Docker)

```bash
docker compose up -d --build
```

API base URL: `http://localhost:8000`

Run smoke test:

```bash
./test_api.sh
```

## Environment variables

All runtime configuration is environment-driven.

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | - | SQLAlchemy PostgreSQL URL used by the app. |
| `HOST` | No | `0.0.0.0` | HTTP bind host. |
| `PORT` | No | `8000` | HTTP bind port (Cloud Run sets this automatically). |
| `LOG_LEVEL` | No | `INFO` | Application log level. |
| `INGESTION_INTERVAL_SECONDS` | No | `3` | Synthetic trade ingestion interval. |
| `DB_POOL_SIZE` | No | `5` | SQLAlchemy connection pool size. |
| `DB_MAX_OVERFLOW` | No | `10` | Extra DB connections allowed above pool size. |
| `DB_POOL_TIMEOUT_SECONDS` | No | `30` | Seconds to wait for an available pooled DB connection. |

## API endpoints

- `GET /health`
- `GET /symbols`
- `GET /price/latest?symbol=AAPL`
- `GET /trades?symbol=AAPL&start=<ISO8601>&end=<ISO8601>&limit=100`
- `GET /candles?symbol=AAPL&interval=1m&start=<ISO8601>&end=<ISO8601>`
- `GET /metrics`
- `GET /status/ingestion`
- `GET /dashboard`

---

## End-to-end GCP setup (run and test without local hosting)

Use this once per new project.

### 1) Set variables and enable APIs

```bash
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export SERVICE_NAME="market-data-platform"
export AR_REPO="market-data"
export DB_INSTANCE="market-data-pg"
export DB_NAME="market_data"
export DB_USER="marketdata"
export DB_PASSWORD="change-me-strong-password"

gcloud config set project "$PROJECT_ID"
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com
```

### 2) Create Artifact Registry repo

```bash
gcloud artifacts repositories create "$AR_REPO" \
  --repository-format=docker \
  --location="$REGION" \
  --description="Docker images for Market Data Platform"
```

### 3) Create Cloud SQL (PostgreSQL)

```bash
gcloud sql instances create "$DB_INSTANCE" \
  --database-version=POSTGRES_15 \
  --cpu=1 \
  --memory=3840MB \
  --region="$REGION"

gcloud sql databases create "$DB_NAME" --instance="$DB_INSTANCE"
gcloud sql users create "$DB_USER" --instance="$DB_INSTANCE" --password="$DB_PASSWORD"
```

### 4) Build and push image

```bash
TAG="$(git rev-parse --short HEAD)"
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${SERVICE_NAME}:${TAG}"

gcloud auth configure-docker "${REGION}-docker.pkg.dev"
docker build -t "$IMAGE_URI" .
docker push "$IMAGE_URI"
```

### 5) Deploy to Cloud Run (Cloud SQL Unix socket)

```bash
INSTANCE_CONNECTION_NAME="$(gcloud sql instances describe "$DB_INSTANCE" --format='value(connectionName)')"
DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@/${DB_NAME}?host=/cloudsql/${INSTANCE_CONNECTION_NAME}"

gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE_URI" \
  --platform managed \
  --region "$REGION" \
  --allow-unauthenticated \
  --add-cloudsql-instances "$INSTANCE_CONNECTION_NAME" \
  --set-env-vars "DATABASE_URL=${DATABASE_URL},LOG_LEVEL=INFO,INGESTION_INTERVAL_SECONDS=3"
```

### 6) Test directly on Cloud Run

```bash
SERVICE_URL="$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)')"

curl -sSf "$SERVICE_URL/health"
curl -sSf "$SERVICE_URL/symbols"
curl -sSf "$SERVICE_URL/status/ingestion"
```

### 7) Observe logs and troubleshoot

```bash
gcloud run services logs read "$SERVICE_NAME" --region "$REGION" --limit=200
```

---

## CI/CD pipeline status

### Is a pipeline created automatically?
No. A deployment pipeline is **not created automatically** just by deploying Cloud Run.

### What is included in this repo now?
A `cloudbuild.yaml` is included to provide a ready Cloud Build pipeline that:
1. Builds the container image.
2. Pushes it to Artifact Registry.
3. Deploys to Cloud Run.

### How to connect pipeline to Git pushes

```bash
gcloud builds triggers create github \
  --name="${SERVICE_NAME}-main" \
  --repo-name="YOUR_GITHUB_REPO" \
  --repo-owner="YOUR_GITHUB_ORG_OR_USER" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.yaml" \
  --substitutions="_REGION=${REGION},_AR_REPO=${AR_REPO},_SERVICE_NAME=${SERVICE_NAME},_INSTANCE_CONNECTION_NAME=${INSTANCE_CONNECTION_NAME},_DATABASE_URL=${DATABASE_URL},_LOG_LEVEL=INFO,_INGESTION_INTERVAL_SECONDS=3"
```

After this, each push to `main` can automatically deploy to Cloud Run.

## Scaling awareness

Cloud Run may run multiple instances. This service does not require local disk state. In-memory runtime metrics are instance-local by design; authoritative market data remains in PostgreSQL.
