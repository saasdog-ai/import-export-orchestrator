#!/bin/bash
# Example script to export data using curl commands

set -e  # Exit on error

# Configuration
BASE_URL="http://localhost:8000"
JWT_TOKEN=""  # Leave empty if auth is disabled (development mode)
ENTITY="bill"

echo "=========================================="
echo "Export API - Step by Step Guide"
echo "=========================================="
echo ""

# Step 1: Health Check
echo "Step 1: Checking service health..."
HEALTH=$(curl -s "${BASE_URL}/health")
echo "$HEALTH" | python3 -m json.tool
echo ""

# Step 2: Preview Data (Optional)
echo "Step 2 (Optional): Previewing data..."
PREVIEW_RESPONSE=$(curl -s -X POST "${BASE_URL}/exports/preview" \
  -H "Content-Type: application/json" \
  ${JWT_TOKEN:+-H "Authorization: Bearer ${JWT_TOKEN}"} \
  -d '{
    "entity": "'"${ENTITY}"'",
    "fields": ["id", "amount", "date", "description", "status"],
    "limit": 5
  }')

echo "$PREVIEW_RESPONSE" | python3 -m json.tool
echo ""

# Step 3: Create Export Job
echo "Step 3: Creating export job..."
EXPORT_REQUEST='{
  "entity": "'"${ENTITY}"'",
  "fields": ["id", "amount", "date", "description", "status", "vendor.name"],
  "filters": {
    "operator": "and",
    "filters": [
      {"field": "amount", "operator": "gt", "value": 500}
    ]
  },
  "sort": [{"field": "date", "direction": "desc"}],
  "limit": 100,
  "offset": 0
}'

echo "Request:"
echo "$EXPORT_REQUEST" | python3 -m json.tool
echo ""

EXPORT_RESPONSE=$(curl -s -X POST "${BASE_URL}/exports" \
  -H "Content-Type: application/json" \
  ${JWT_TOKEN:+-H "Authorization: Bearer ${JWT_TOKEN}"} \
  -d "$EXPORT_REQUEST")

echo "Response:"
echo "$EXPORT_RESPONSE" | python3 -m json.tool
echo ""

# Extract run_id
RUN_ID=$(echo "$EXPORT_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['run_id'])" 2>/dev/null || echo "")

if [ -z "$RUN_ID" ]; then
  echo "❌ Failed to create export job"
  exit 1
fi

echo "✅ Export job created. Run ID: ${RUN_ID}"
echo ""

# Step 4: Wait for Job to Complete
echo "Step 4: Waiting for export to complete..."
MAX_WAIT=30
WAIT_COUNT=0
STATUS="pending"

while [ "$STATUS" != "succeeded" ] && [ "$STATUS" != "failed" ] && [ $WAIT_COUNT -lt $MAX_WAIT ]; do
  sleep 2
  WAIT_COUNT=$((WAIT_COUNT + 2))
  
  RESULT_RESPONSE=$(curl -s -X GET "${BASE_URL}/exports/${RUN_ID}/result" \
    ${JWT_TOKEN:+-H "Authorization: Bearer ${JWT_TOKEN}"})
  
  STATUS=$(echo "$RESULT_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "unknown")
  echo "  Status: ${STATUS} (waited ${WAIT_COUNT}s)"
done

echo ""
echo "Final Status:"
echo "$RESULT_RESPONSE" | python3 -m json.tool
echo ""

if [ "$STATUS" == "failed" ]; then
  ERROR_MSG=$(echo "$RESULT_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('error_message', 'Unknown error'))" 2>/dev/null || echo "Unknown error")
  echo "❌ Export failed: ${ERROR_MSG}"
  exit 1
fi

if [ "$STATUS" != "succeeded" ]; then
  echo "⚠️  Export did not complete within ${MAX_WAIT} seconds. Status: ${STATUS}"
  exit 1
fi

# Step 5: Get Download URL
echo "Step 5: Getting download URL..."
DOWNLOAD_RESPONSE=$(curl -s -X GET "${BASE_URL}/exports/${RUN_ID}/download?expiration_seconds=3600" \
  ${JWT_TOKEN:+-H "Authorization: Bearer ${JWT_TOKEN}"})

echo "$DOWNLOAD_RESPONSE" | python3 -m json.tool
echo ""

DOWNLOAD_URL=$(echo "$DOWNLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['download_url'])" 2>/dev/null || echo "")

if [ -z "$DOWNLOAD_URL" ]; then
  echo "⚠️  No download URL available. File may be stored locally."
  FILE_PATH=$(echo "$RESULT_RESPONSE" | python3 -c "import sys, json; meta = json.load(sys.stdin).get('result_metadata', {}); print(meta.get('local_file_path', meta.get('remote_file_path', '')))" 2>/dev/null || echo "")
  if [ -n "$FILE_PATH" ]; then
    echo "File path: ${FILE_PATH}"
    echo "To access file in Docker container:"
    echo "  docker exec job_runner_app cat ${FILE_PATH}"
  fi
  exit 0
fi

echo "✅ Download URL obtained"
echo ""

# Step 6: Download the File
echo "Step 6: Downloading file..."
OUTPUT_FILE="exported_${ENTITY}_$(date +%Y%m%d_%H%M%S).csv"
curl -s -o "${OUTPUT_FILE}" "${DOWNLOAD_URL}"

if [ -f "${OUTPUT_FILE}" ]; then
  FILE_SIZE=$(wc -c < "${OUTPUT_FILE}")
  echo "✅ File downloaded: ${OUTPUT_FILE} (${FILE_SIZE} bytes)"
  echo ""
  echo "First few lines:"
  head -5 "${OUTPUT_FILE}"
else
  echo "❌ Failed to download file"
  exit 1
fi

echo ""
echo "=========================================="
echo "Export completed successfully!"
echo "=========================================="

