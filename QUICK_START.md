# Quick Start Guide

## 🚀 Get Running in 30 Seconds

```bash
cd market-data-platform
docker compose up
```

Wait for this message:
```
market-data-api | INFO - Application started successfully
market-data-api | INFO - Generated 5 trades at 2026-02-08T10:30:00
```

## 🧪 Test It Works

Open your browser to:
- **http://localhost:8000** - API info
- **http://localhost:8000/docs** - Interactive API docs
- **http://localhost:8000/health** - Health check

Or use curl:
```bash
# Check health
curl http://localhost:8000/health

# See all symbols
curl http://localhost:8000/symbols

# Get Apple stock price
curl "http://localhost:8000/price/latest?symbol=AAPL"

# Watch it change (requires watch command)
watch -n 2 'curl -s "http://localhost:8000/price/latest?symbol=AAPL"'
```

## 📊 What You'll See

**Health Check Response:**
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

**Symbols Response:**
```json
{
  "symbols": [
    {"symbol": "AAPL", "name": "Apple Inc.", "created_at": "..."},
    {"symbol": "AMZN", "name": "Amazon.com Inc.", "created_at": "..."},
    {"symbol": "GOOGL", "name": "Alphabet Inc.", "created_at": "..."},
    {"symbol": "MSFT", "name": "Microsoft Corporation", "created_at": "..."},
    {"symbol": "TSLA", "name": "Tesla Inc.", "created_at": "..."}
  ],
  "count": 5
}
```

**Price Response (changes every 3 seconds):**
```json
{
  "symbol": "AAPL",
  "price": 185.42,
  "volume": 45678.90,
  "timestamp": "2026-02-08T10:30:00Z"
}
```

## 🔍 What's Happening Behind the Scenes

```
┌─────────────────────────────────────────┐
│  Every 3 seconds, automatically:        │
│                                         │
│  1. Generate new prices (±2% change)   │
│  2. Create trade records               │
│  3. Save to PostgreSQL                 │
│  4. Log success                        │
│                                         │
│  You'll see in logs:                   │
│  "Generated 5 trades at [timestamp]"   │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  When you query /price/latest:          │
│                                         │
│  1. API receives request               │
│  2. Validates symbol exists            │
│  3. Queries database for latest trade  │
│  4. Returns JSON response              │
│                                         │
│  Response time: ~10-20ms               │
└─────────────────────────────────────────┘
```

## 📁 File Overview

```
market-data-platform/
│
├── 📄 docker-compose.yml    ← Start here: defines DB + API
├── 📄 Dockerfile            ← How API container is built
├── 📄 requirements.txt      ← Python dependencies
│
├── 📂 app/                  ← Application code
│   ├── main.py             ← Entry point (runs everything)
│   ├── api.py              ← REST endpoints
│   ├── ingestion.py        ← Auto-generates trades
│   ├── database.py         ← DB connection
│   ├── models.py           ← Database tables
│   ├── schemas.py          ← API request/response types
│   └── config.py           ← Environment variables
│
└── 📚 Documentation/
    ├── README.md           ← User guide
    ├── ARCHITECTURE.md     ← Detailed design
    └── IMPLEMENTATION_SUMMARY.md ← How to extend
```

## 🛠️ Common Commands

```bash
# Start services
docker compose up

# Start in background
docker compose up -d

# View logs
docker compose logs -f api

# Stop everything
docker compose down

# Stop and delete all data
docker compose down -v

# Restart just the API
docker compose restart api

# Access database directly
docker exec -it market-data-db psql -U marketdata -d market_data
```

## 🔧 Configuration

Edit `docker-compose.yml` to change:

```yaml
environment:
  DATABASE_URL: postgresql://user:pass@host:5432/dbname
  LOG_LEVEL: INFO              # DEBUG, INFO, WARNING, ERROR
  INGESTION_INTERVAL_SECONDS: 3  # How often to generate trades
```

## 🐛 Troubleshooting

**Port 8000 already in use?**
```yaml
# In docker-compose.yml, change:
ports:
  - "8001:8000"  # Use 8001 instead
```

**Database won't start?**
```bash
# Check status
docker compose ps

# View DB logs
docker compose logs postgres

# Restart database
docker compose restart postgres
```

**No data appearing?**
```bash
# Check ingestion is running
docker compose logs -f api | grep "Generated"

# Should see:
# INFO - Generated 5 trades at 2026-02-08T...
```

**Want fresh start?**
```bash
docker compose down -v  # Deletes database
docker compose up       # Starts fresh
```

## 📚 Learn More

- **README.md** - Complete usage guide
- **ARCHITECTURE.md** - System design and diagrams
- **IMPLEMENTATION_SUMMARY.md** - How to extend for Phase 2+

## ✅ Verification Checklist

After running `docker compose up`, verify:

- [ ] Both containers are running: `docker compose ps`
- [ ] No errors in logs: `docker compose logs`
- [ ] Health endpoint works: `curl http://localhost:8000/health`
- [ ] Symbols are listed: `curl http://localhost:8000/symbols`
- [ ] Prices are returned: `curl "http://localhost:8000/price/latest?symbol=AAPL"`
- [ ] Prices change over time: Query multiple times, see different values
- [ ] API docs accessible: Open http://localhost:8000/docs

## 🎯 What This Achieves

You now have a **production-ready microservice** that:

✅ Serves as authoritative source of price data  
✅ Runs independently with its own database  
✅ Exposes stable REST APIs  
✅ Auto-generates realistic market data  
✅ Is ready for other services to integrate  
✅ Can be deployed to cloud  
✅ Can be extended without breaking contracts  

**This is the foundation.** Next phases will add candles, observability, and production features.

## 🚀 Ready to Integrate?

Other services can now call:
```python
import requests

# In any other service:
price = requests.get(
    "http://market-data-platform:8000/price/latest",
    params={"symbol": "AAPL"}
).json()

print(f"Current AAPL price: ${price['price']}")
```

**That's it! You have a working Market Data Platform.**
