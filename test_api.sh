#!/bin/bash
# Quick test script to validate API endpoints
# Run this after starting the service with docker compose up

set -e

BASE_URL="http://localhost:8000"
END_TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
START_TS=$(date -u -d '10 minutes ago' +"%Y-%m-%dT%H:%M:%SZ")

print_json() {
  if command -v jq >/dev/null 2>&1; then
    jq .
  elif command -v python3 >/dev/null 2>&1; then
    python3 -m json.tool
  else
    cat
  fi
}

echo "======================================"
echo "Market Data Platform API Test (Phase 3)"
echo "======================================"
echo ""

if ! command -v jq >/dev/null 2>&1; then
  echo "[WARN] jq not found. Falling back to python3 -m json.tool (or raw output)."
  echo ""
fi

echo "1. Testing Health Endpoint..."
curl -s "${BASE_URL}/health" | print_json
echo ""
echo ""

echo "2. Testing Symbols Endpoint..."
curl -s "${BASE_URL}/symbols" | print_json
echo ""
echo ""

echo "3. Testing Latest Price for AAPL..."
curl -s "${BASE_URL}/price/latest?symbol=AAPL" | print_json
echo ""
echo ""

echo "4. Testing Latest Price for GOOGL..."
curl -s "${BASE_URL}/price/latest?symbol=GOOGL" | print_json
echo ""
echo ""

echo "5. Testing Latest Price for MSFT..."
curl -s "${BASE_URL}/price/latest?symbol=MSFT" | print_json
echo ""
echo ""

echo "6. Testing Trades Endpoint (last 10 minutes for AAPL)..."
curl -s "${BASE_URL}/trades?symbol=AAPL&start=${START_TS}&end=${END_TS}&limit=100" | print_json
echo ""
echo ""

echo "7. Testing Candles Endpoint (1m, last 10 minutes for AAPL)..."
curl -s "${BASE_URL}/candles?symbol=AAPL&interval=1m&start=${START_TS}&end=${END_TS}" | print_json
echo ""
echo ""

echo "8. Testing Metrics Endpoint..."
curl -s "${BASE_URL}/metrics" | print_json
echo ""
echo ""

echo "9. Testing Ingestion Status Endpoint..."
curl -s "${BASE_URL}/status/ingestion" | print_json
echo ""
echo ""

echo "10. Testing Dashboard Endpoint (HTML head)..."
curl -s "${BASE_URL}/dashboard" | head -n 20
echo ""
echo ""

echo "======================================"
echo "All tests completed!"
echo "======================================"
echo ""
if command -v jq >/dev/null 2>&1; then
  echo "Watch prices update in real-time:"
  echo "  watch -n 2 'curl -s ${BASE_URL}/price/latest?symbol=AAPL | jq .'"
else
  echo "Watch prices update in real-time:"
  echo "  watch -n 2 'curl -s ${BASE_URL}/price/latest?symbol=AAPL | python3 -m json.tool'"
fi
