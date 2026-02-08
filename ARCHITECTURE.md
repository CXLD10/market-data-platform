# Architecture Documentation

## System Overview

The Market Data Platform is designed as a production-ready microservice that serves as the single source of truth for price data in a distributed fintech ecosystem.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    External Systems                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Quant/ML   │  │  Portfolio   │  │   Billing    │      │
│  │    Engine    │  │   Manager    │  │   System     │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │               │
│         │  HTTP APIs      │                 │               │
│         │                 │                 │               │
└─────────┼─────────────────┼─────────────────┼───────────────┘
          │                 │                 │
          └─────────────────┴─────────────────┘
                            │
                            ▼
          ┌─────────────────────────────────┐
          │     Market Data Platform        │
          │                                 │
          │  ┌──────────────────────────┐   │
          │  │    FastAPI REST API      │   │
          │  │                          │   │
          │  │  GET /health            │   │
          │  │  GET /symbols           │   │
          │  │  GET /price/latest      │   │
          │  │                          │   │
          │  └──────────┬───────────────┘   │
          │             │                   │
          │  ┌──────────▼───────────────┐   │
          │  │  Application Layer       │   │
          │  │                          │   │
          │  │  • Request Validation    │   │
          │  │  • Business Logic        │   │
          │  │  • Error Handling        │   │
          │  │  • Logging               │   │
          │  │                          │   │
          │  └──────────┬───────────────┘   │
          │             │                   │
          │  ┌──────────▼───────────────┐   │
          │  │   Database Layer         │   │
          │  │                          │   │
          │  │  • Connection Pooling    │   │
          │  │  • Session Management    │   │
          │  │  • ORM (SQLAlchemy)      │   │
          │  │                          │   │
          │  └──────────┬───────────────┘   │
          │             │                   │
          │  ┌──────────▼───────────────┐   │
          │  │  Background Services     │   │
          │  │                          │   │
          │  │  ┌──────────────────┐    │   │
          │  │  │ Ingestion Loop   │    │   │
          │  │  │                  │    │   │
          │  │  │ • Generate Data  │    │   │
          │  │  │ • Random Walk    │    │   │
          │  │  │ • Persist Trades │    │   │
          │  │  │ • Every 3s       │    │   │
          │  │  └──────────────────┘    │   │
          │  │                          │   │
          │  └──────────────────────────┘   │
          │                                 │
          └─────────────────────────────────┘
                            │
                            ▼
          ┌─────────────────────────────────┐
          │      PostgreSQL Database        │
          │                                 │
          │  ┌────────────────────────┐     │
          │  │  symbols               │     │
          │  │  ─────────────────     │     │
          │  │  • id (PK)            │     │
          │  │  • symbol (unique)    │     │
          │  │  • name               │     │
          │  │  • created_at         │     │
          │  └────────────────────────┘     │
          │                                 │
          │  ┌────────────────────────┐     │
          │  │  trades                │     │
          │  │  ─────────────────     │     │
          │  │  • id (PK)            │     │
          │  │  • symbol (FK)        │     │
          │  │  • price              │     │
          │  │  • volume             │     │
          │  │  • timestamp (idx)    │     │
          │  │  • created_at         │     │
          │  └────────────────────────┘     │
          │                                 │
          │  Indexes:                       │
          │  • symbol (unique)              │
          │  • timestamp                    │
          │  • (symbol, timestamp)          │
          │                                 │
          └─────────────────────────────────┘
```

## Component Breakdown

### 1. REST API Layer (`app/api.py`)
**Responsibility:** Expose stable HTTP endpoints for data consumers

- **GET /health**: Service health check with database connectivity
- **GET /symbols**: List all available trading symbols
- **GET /price/latest**: Get most recent price for a symbol

**Key Features:**
- Pydantic schema validation
- Dependency injection for database sessions
- Comprehensive error handling
- Automatic interactive documentation (Swagger/ReDoc)

### 2. Application Layer
**Files:** `app/main.py`, `app/config.py`, `app/schemas.py`

**Responsibilities:**
- Application lifecycle management
- Configuration via environment variables
- Request/response schema definitions
- Structured logging

**Key Features:**
- Lifespan context manager for startup/shutdown
- Type-safe configuration with Pydantic
- No hardcoded values

### 3. Database Layer (`app/database.py`, `app/models.py`)
**Responsibility:** Data persistence and retrieval

**Features:**
- Connection pooling for efficiency
- Context managers for safe session handling
- Automatic schema initialization
- Pre-ping health checks

**Models:**
- **Symbol**: Trading symbols (AAPL, GOOGL, etc.)
- **Trade**: Individual trade events with price and volume

### 4. Ingestion Service (`app/ingestion.py`)
**Responsibility:** Generate and persist synthetic market data

**How It Works:**
1. Initializes default symbols on startup
2. Maintains state of last prices for random walk
3. Every N seconds (configurable):
   - Updates prices using random walk algorithm (±2%)
   - Generates realistic volume
   - Creates trade records
   - Persists to database
4. Continues indefinitely with error recovery

**Design Principles:**
- Idempotent initialization (safe to restart)
- Non-blocking async operation
- Graceful error handling
- Structured logging for observability

## Data Flow

### Ingestion Flow
```
Timer (3s) → Generate Prices → Create Trades → Database → Log Success
     ↓                                           ↓
  Error? ────────────────────── Retry ──────────┘
```

### Query Flow
```
HTTP Request → FastAPI Router → Validation → Database Query → Response
      │                            │              │
      │                            ▼              │
      │                         Error? ───────────┘
      │                            │
      └────────────────────────────┘
                                   │
                               JSON Response
```

## Deployment Architecture

### Local Development
```
docker-compose up
     │
     ├─→ PostgreSQL Container (port 5432)
     │     • Volume-mounted data
     │     • Health checks enabled
     │
     └─→ API Container (port 8000)
           • Waits for DB health
           • Auto-restarts on failure
           • Logs to stdout
```

### Cloud Deployment (Future)
```
Load Balancer
     │
     ├─→ API Instance 1 ─┐
     ├─→ API Instance 2 ─┼─→ Managed PostgreSQL
     └─→ API Instance N ─┘       (RDS/Cloud SQL)
```

## Design Decisions

### 1. Why FastAPI?
- Modern async Python framework
- Automatic OpenAPI documentation
- Built-in validation with Pydantic
- High performance
- Industry standard for microservices

### 2. Why PostgreSQL?
- ACID compliance for financial data
- Excellent time-series performance
- Rich indexing capabilities
- Industry standard for transactional data
- Easy to scale (read replicas, partitioning)

### 3. Why SQLAlchemy?
- Database agnostic ORM
- Safe SQL generation
- Migration support (future Alembic integration)
- Connection pooling
- Type safety

### 4. Why Separate Ingestion Service?
- Decouples data generation from API serving
- Independent scaling (can run multiple ingestors)
- Easier testing (can disable for API tests)
- Clear responsibility separation

### 5. Why Environment Variables?
- 12-factor app compliance
- Easy to configure per environment
- No secrets in code
- Cloud-native pattern

## Extension Points

### Adding New Endpoints
1. Define Pydantic schema in `app/schemas.py`
2. Add route in `app/api.py`
3. Test with automatic `/docs` UI

### Adding New Data Models
1. Create model in `app/models.py`
2. Run service - schema auto-creates
3. Access via ORM in endpoints

### Changing Ingestion Logic
1. Edit `app/ingestion.py`
2. Modify `generate_price_movement()` for algorithm
3. Adjust `INGESTION_INTERVAL_SECONDS` for frequency

### Adding External Data Sources
1. Create new ingestion service
2. Implement same interface
3. Run alongside synthetic ingestion

## Security Considerations (Phase 1)

**Current State:**
- No authentication (internal service assumption)
- No rate limiting
- Database credentials in environment (acceptable for local dev)

**Future Phases:**
- API key authentication
- Rate limiting per consumer
- Secrets management (Vault, AWS Secrets Manager)
- Network policies
- TLS/SSL for database connections

## Observability

### Logging
- Structured JSON logs (can enable)
- Request/response logging
- Error stack traces
- Ingestion heartbeat

### Metrics (Future)
- Request latency
- Error rates
- Database connection pool stats
- Ingestion lag

### Health Checks
- `/health` endpoint
- Database connectivity
- Last ingestion timestamp
- Trade count

## Performance Characteristics

### Current Performance
- ~10-20ms latency for latest price queries
- 5 symbols × 1 trade per interval = minimal load
- Database can handle 10k+ writes/sec
- API can handle 1000+ req/sec on single instance

### Scaling Strategy (Future)
1. Horizontal: Add more API instances behind load balancer
2. Read replicas: Separate read/write workloads
3. Caching: Redis for hot paths
4. Partitioning: Time-based table partitioning for trades

## Integration Guide

### For Downstream Services

**Base URL:** `http://market-data-platform:8000`

**Example: Quant Engine**
```python
import requests

# Get latest price for analysis
response = requests.get(
    "http://market-data-platform:8000/price/latest",
    params={"symbol": "AAPL"}
)
price_data = response.json()

# Use in model
current_price = price_data["price"]
```

**Example: Portfolio Manager**
```python
# Get all symbols
symbols = requests.get(
    "http://market-data-platform:8000/symbols"
).json()

# Fetch prices for portfolio
for symbol in symbols["symbols"]:
    price = requests.get(
        "http://market-data-platform:8000/price/latest",
        params={"symbol": symbol["symbol"]}
    ).json()
    # Update portfolio value
```

**Best Practices:**
- Check `/health` before making requests
- Implement retries with exponential backoff
- Cache responses when appropriate
- Handle 404s gracefully (symbol may not exist)
- Monitor response times

## Testing Strategy

### Manual Testing
```bash
# Start service
docker compose up

# Run test script
./test_api.sh
```

### Integration Testing (Future)
- Pytest with test database
- Factory patterns for test data
- API client fixtures

### Load Testing (Future)
- Locust or k6 for load generation
- Target: 1000 req/sec
- Monitor database connection pool

## Troubleshooting

### Common Issues

**Database connection refused**
- Check PostgreSQL health: `docker compose ps`
- Verify DATABASE_URL is correct
- Ensure DB container started first

**No data appearing**
- Check ingestion logs: `docker compose logs -f api`
- Verify symbols were initialized
- Check database directly: `SELECT * FROM trades LIMIT 10`

**Slow queries**
- Check indexes: `\d trades` in psql
- Verify composite index on (symbol, timestamp)
- Review query patterns in logs

## Next Steps

After Phase 1 is validated, proceed to:

1. **Phase 2 - OHLC Candles**: Aggregate trades into time-based candles
2. **Phase 3 - Observability**: Add metrics and monitoring
3. **Phase 4 - Production Hardening**: Auth, pagination, caching
4. **Phase 5 - Cloud Deployment**: Kubernetes, managed services

Each phase builds on the stable foundation established in Phase 1.
