# Market Data Platform - Phase 1

A production-oriented time-series service that acts as the authoritative source of financial price information for a broader fintech ecosystem.

## Overview

This is **Phase 1** - a minimal but production-ready vertical slice that:
- Runs locally in Docker
- Persists data in Postgres
- Exposes stable REST endpoints
- Generates synthetic market data automatically
- Can be extended without breaking contracts

## Quick Start

### Prerequisites
- Docker and Docker Compose
- curl or a web browser for testing

### Run the Platform

```bash
docker compose up
```

The service will automatically:
1. Start PostgreSQL database
2. Initialize the schema
3. Begin generating synthetic trades every 3 seconds
4. Expose REST APIs on `http://localhost:8000`

### Test the APIs

**Health Check:**
```bash
curl http://localhost:8000/health
```

**List Available Symbols:**
```bash
curl http://localhost:8000/symbols
```

**Get Latest Price:**
```bash
curl "http://localhost:8000/price/latest?symbol=AAPL"
```

**Watch Prices Change:**
```bash
# Run this multiple times to see prices update
watch -n 2 'curl -s "http://localhost:8000/price/latest?symbol=AAPL"'
```

### Interactive Documentation

FastAPI provides automatic interactive documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Contract

### GET /health
Returns service health and database status.

**Response:**
```json
{
  "status": "healthy",
  "service": "market-data-platform",
  "database": "healthy",
  "timestamp": "2026-02-08T10:30:00Z",
  "last_trade_count": 150,
  "last_ingestion": "2026-02-08T10:29:57Z"
}
```

### GET /symbols
Returns all available symbols.

**Response:**
```json
{
  "symbols": [
    {
      "symbol": "AAPL",
      "name": "Apple Inc.",
      "created_at": "2026-02-08T10:00:00Z"
    }
  ],
  "count": 5
}
```

### GET /price/latest?symbol=AAPL
Returns the latest price for a symbol.

**Query Parameters:**
- `symbol` (required): Symbol code (e.g., AAPL, GOOGL)

**Response:**
```json
{
  "symbol": "AAPL",
  "price": 185.42,
  "volume": 45678.90,
  "timestamp": "2026-02-08T10:30:00Z"
}
```

## Project Structure

```
market-data-platform/
├── app/
│   ├── __init__.py          # Package initialization
│   ├── main.py              # Application entry point
│   ├── config.py            # Environment-based configuration
│   ├── database.py          # Database connection & session management
│   ├── models.py            # SQLAlchemy ORM models
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── api.py               # FastAPI REST endpoints
│   └── ingestion.py         # Synthetic data generation service
├── docker-compose.yml       # Local development setup
├── Dockerfile              # Application container
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Configuration

All configuration is driven by environment variables (see `docker-compose.yml`):

- `DATABASE_URL`: PostgreSQL connection string
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)
- `INGESTION_INTERVAL_SECONDS`: Frequency of synthetic data generation

## How It Works

### Database Schema

**symbols table:**
- Stores available trading symbols (AAPL, GOOGL, etc.)
- Created on first startup

**trades table:**
- Stores individual trade events
- Indexed by symbol and timestamp for efficient queries
- Grows continuously as ingestion runs

### Ingestion Service

The ingestion service runs in the background and:
1. Initializes 5 default symbols on startup (AAPL, GOOGL, MSFT, TSLA, AMZN)
2. Every 3 seconds (configurable):
   - Generates new prices using random walk algorithm
   - Creates trade records with realistic volume
   - Persists to database
3. Continues indefinitely with error recovery

Prices move realistically within ±2% per interval, creating believable market behavior.

### REST APIs

All endpoints follow consistent patterns:
- Use Pydantic schemas for validation
- Return structured JSON responses
- Include proper error handling
- Log all operations

## Design Principles

### 1. API Stability
All endpoints are designed to be stable contracts. Future changes will be **additive only** to avoid breaking downstream consumers.

### 2. Independent Service
This service is intentionally isolated:
- No shared databases with other systems
- All integration via HTTP APIs
- Environment-driven configuration
- No hardcoded dependencies

### 3. Reliability First
- Database connection pooling with health checks
- Automatic schema initialization
- Ingestion continues despite errors
- Graceful shutdown handling

### 4. Cloud-Ready
- Container-first design
- 12-factor app principles
- Stateless application (state in database)
- Environment variable configuration

## Development

### View Logs
```bash
docker compose logs -f api
```

### Restart Service
```bash
docker compose restart api
```

### Stop Everything
```bash
docker compose down
```

### Clean Database (Start Fresh)
```bash
docker compose down -v
docker compose up
```

### Direct Database Access
```bash
docker exec -it market-data-db psql -U marketdata -d market_data
```

## Next Phases

This Phase 1 implementation provides the foundation. Future phases will add:

**Phase 2 - OHLC Candles:**
- Aggregate trades into time-based candles
- `/candles` endpoint
- Efficient time-series queries

**Phase 3 - Observability:**
- Prometheus metrics
- Structured logging
- Ingestion heartbeat monitoring

**Phase 4 - Production Hardening:**
- Pagination for large result sets
- Rate limiting
- Authentication/authorization
- Caching layer

**Phase 5 - Cloud Deployment:**
- Kubernetes manifests
- Cloud database integration
- Horizontal scaling
- Distributed tracing

## Extending the System

The current architecture makes it easy to extend:

### Add New Symbols
Edit `app/ingestion.py` and add to `DEFAULT_SYMBOLS`:
```python
DEFAULT_SYMBOLS = [
    ("AAPL", "Apple Inc."),
    ("NEW", "New Company Inc."),  # Add here
]
```

### Add New Endpoints
Create new routes in `app/api.py`:
```python
@api.get("/your-new-endpoint")
async def your_endpoint(db: Session = Depends(get_db)):
    # Implementation
    pass
```

### Modify Ingestion Logic
Edit `app/ingestion.py`:
- Change price movement algorithm
- Adjust volume generation
- Add new data sources

### Add New Models
Add tables in `app/models.py` and they'll be created automatically.

## Troubleshooting

**Database connection failed:**
- Ensure PostgreSQL container is healthy: `docker compose ps`
- Check logs: `docker compose logs postgres`

**No data appearing:**
- Check ingestion logs: `docker compose logs -f api`
- Verify ingestion service is running

**Port already in use:**
- Change port in `docker-compose.yml` ports section
- Or stop conflicting service

## License

Internal use only - Part of broader fintech ecosystem.
