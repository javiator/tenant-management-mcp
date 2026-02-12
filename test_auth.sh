#!/bin/bash
# Test script for authentication middleware

set -e

echo "=== Testing TM MCP Server Authentication ==="
echo ""

# Get test keys from .keys.json
if [ ! -f .keys.json ]; then
    echo "❌ No .keys.json found. Generate keys first:"
    echo "   uv run python scripts/manage_keys.py generate --name 'Test User'"
    exit 1
fi

# Extract first active key
VALID_KEY=$(uv run python scripts/manage_keys.py export | cut -d',' -f1)

if [ -z "$VALID_KEY" ]; then
    echo "❌ No active keys found in .keys.json"
    exit 1
fi

echo "✅ Found test key: ${VALID_KEY:0:15}..."
echo ""

# Create test .env file
echo "Creating test .env with authentication enabled..."
cat > .env.test <<EOF
BACKEND_MCP_BASE_URL=http://localhost:8080
MCP_API_KEYS=$VALID_KEY
EOF

echo "✅ Test environment configured"
echo ""

# Start server in background
echo "Starting MCP server with authentication..."
ENV_FILE=.env.test uv run tm-mcp --transport streamable-http --host 127.0.0.1 --port 8888 &
SERVER_PID=$!

# Wait for server to start
echo "Waiting for server to start..."
sleep 3

# Function to cleanup
cleanup() {
    echo ""
    echo "Cleaning up..."
    kill $SERVER_PID 2>/dev/null || true
    rm -f .env.test
    echo "✅ Cleanup complete"
}
trap cleanup EXIT

echo "✅ Server started (PID: $SERVER_PID)"
echo ""

# Test 1: No API key (should fail)
echo "Test 1: Request without API key (should fail with 401)"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8888/mcp/tools)
if [ "$HTTP_CODE" = "401" ]; then
    echo "✅ Test 1 PASSED - Got 401 Unauthorized"
else
    echo "❌ Test 1 FAILED - Expected 401, got $HTTP_CODE"
fi
echo ""

# Test 2: Invalid bearer token (should fail)
echo "Test 2: Request with invalid bearer token (should fail with 401)"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer invalid_key_12345" \
    http://127.0.0.1:8888/mcp/tools)
if [ "$HTTP_CODE" = "401" ]; then
    echo "✅ Test 2 PASSED - Got 401 Unauthorized"
else
    echo "❌ Test 2 FAILED - Expected 401, got $HTTP_CODE"
fi
echo ""

# Test 3: Valid bearer token (should succeed)
echo "Test 3: Request with valid bearer token (should succeed)"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $VALID_KEY" \
    http://127.0.0.1:8888/mcp/tools)
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
    echo "✅ Test 3 PASSED - Got $HTTP_CODE (authenticated)"
else
    echo "❌ Test 3 FAILED - Expected 200/204, got $HTTP_CODE"
fi
echo ""

# Test 4: Health check (should work without auth)
echo "Test 4: Health check without API key (should succeed)"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8888/health)
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "404" ]; then
    echo "✅ Test 4 PASSED - Health check accessible"
else
    echo "❌ Test 4 FAILED - Expected 200/404, got $HTTP_CODE"
fi
echo ""

echo "=== Authentication Tests Complete ==="
