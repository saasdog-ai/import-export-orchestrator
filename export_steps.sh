#!/bin/bash
# Simple step-by-step export guide

echo "=== Step 1: Health Check ==="
curl -s http://localhost:8000/health | python3 -m json.tool
echo ""

echo "=== Step 2: Create Export Job ==="
echo "Command:"
echo 'curl -X POST http://localhost:8000/exports \'
echo '  -H "Content-Type: application/json" \'
echo '  -d '"'"'{"entity": "bill", "fields": ["id", "amount", "date"], "limit": 10}'"'"''
echo ""
echo "Response:"
RESPONSE=$(curl -s -X POST http://localhost:8000/exports \
  -H "Content-Type: application/json" \
  -d '{"entity": "bill", "fields": ["id", "amount", "date"], "limit": 10}')
echo "$RESPONSE" | python3 -m json.tool
RUN_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['run_id'])" 2>/dev/null)
echo ""
echo "Run ID: $RUN_ID"
echo ""

echo "=== Step 3: Check Job Status (wait 2 seconds) ==="
sleep 2
echo "Command:"
echo "curl -s http://localhost:8000/exports/$RUN_ID/result"
echo ""
echo "Response:"
curl -s http://localhost:8000/exports/$RUN_ID/result | python3 -m json.tool
echo ""

echo "=== Step 4: Get Download URL ==="
echo "Command:"
echo "curl -s \"http://localhost:8000/exports/$RUN_ID/download\""
echo ""
echo "Response:"
curl -s "http://localhost:8000/exports/$RUN_ID/download" | python3 -m json.tool
