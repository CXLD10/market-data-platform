#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "Testing Market Data Gateway at ${BASE_URL}"

curl -fsS "${BASE_URL}/health" | python -m json.tool
curl -fsS "${BASE_URL}/readiness" | python -m json.tool
curl -fsS "${BASE_URL}/quote?symbol=INFY&exchange=NSE" | python -m json.tool
curl -fsS "${BASE_URL}/historical?symbol=AAPL&exchange=NASDAQ&period=1mo" | python -m json.tool
curl -fsS "${BASE_URL}/search?query=INFY" | python -m json.tool
curl -fsS "${BASE_URL}/metrics" | python -m json.tool
curl -fsS "${BASE_URL}/exchanges/status" | python -m json.tool
curl -fsS "${BASE_URL}/market-status?exchange=NSE" | python -m json.tool

echo "All endpoint checks completed."
