#!/bin/bash
# Quick test script to validate API endpoints
# Run this after starting the service with docker compose up

set -e

BASE_URL="http://localhost:8000"

echo "======================================"
echo "Market Data Platform API Test"
echo "======================================"
echo ""

echo "1. Testing Health Endpoint..."
curl -s "${BASE_URL}/health" | jq .
echo ""
echo ""

echo "2. Testing Symbols Endpoint..."
curl -s "${BASE_URL}/symbols" | jq .
echo ""
echo ""

echo "3. Testing Latest Price for AAPL..."
curl -s "${BASE_URL}/price/latest?symbol=AAPL" | jq .
echo ""
echo ""

echo "4. Testing Latest Price for GOOGL..."
curl -s "${BASE_URL}/price/latest?symbol=GOOGL" | jq .
echo ""
echo ""

echo "5. Testing Latest Price for MSFT..."
curl -s "${BASE_URL}/price/latest?symbol=MSFT" | jq .
echo ""
echo ""

echo "======================================"
echo "All tests completed!"
echo "======================================"
echo ""
echo "Watch prices update in real-time:"
echo "  watch -n 2 'curl -s ${BASE_URL}/price/latest?symbol=AAPL | jq .'"
