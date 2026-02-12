#!/bin/bash
# Test Docker build and run locally
#
# Usage:
#   ./test_docker.sh           # Build and run
#   ./test_docker.sh --skip-build  # Skip build, just run

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

IMAGE_NAME="tm-mcp-test"
CONTAINER_NAME="tm-mcp-test-container"
PORT=8888

# Parse arguments
SKIP_BUILD=false
if [ "$1" == "--skip-build" ]; then
    SKIP_BUILD=true
fi

echo -e "${GREEN}=== Testing TM MCP Docker Build ===${NC}"
echo ""

# Build image
if [ "$SKIP_BUILD" = false ]; then
    echo -e "${YELLOW}Building Docker image...${NC}"
    docker build -t $IMAGE_NAME .
    echo -e "${GREEN}✅ Build complete${NC}"
    echo ""
else
    echo -e "${YELLOW}Skipping build (using existing image)${NC}"
    echo ""
fi

# Get test API key
if [ -f .keys.json ]; then
    echo -e "${YELLOW}Getting test API key...${NC}"
    TEST_KEY=$(uv run python scripts/manage_keys.py export | cut -d',' -f1)
    echo -e "${GREEN}✅ Using key: ${TEST_KEY:0:15}...${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠️  No .keys.json found - starting without authentication${NC}"
    TEST_KEY=""
    echo ""
fi

# Stop and remove existing container if it exists
echo -e "${YELLOW}Cleaning up any existing containers...${NC}"
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true
echo ""

# Run container
echo -e "${YELLOW}Starting container...${NC}"
docker run -d \
    --name $CONTAINER_NAME \
    -p $PORT:8000 \
    -e BACKEND_MCP_BASE_URL=http://host.docker.internal:8080 \
    -e MCP_API_KEYS="$TEST_KEY" \
    $IMAGE_NAME

echo -e "${GREEN}✅ Container started${NC}"
echo ""

# Wait for container to be ready
echo -e "${YELLOW}Waiting for server to start...${NC}"
sleep 3

# Check if container is running
if ! docker ps | grep -q $CONTAINER_NAME; then
    echo -e "${RED}❌ Container failed to start${NC}"
    echo ""
    echo "Logs:"
    docker logs $CONTAINER_NAME
    docker rm $CONTAINER_NAME
    exit 1
fi

echo -e "${GREEN}✅ Server is running${NC}"
echo ""

# Function to cleanup
cleanup() {
    echo ""
    echo -e "${YELLOW}Cleaning up...${NC}"
    docker stop $CONTAINER_NAME 2>/dev/null || true
    docker rm $CONTAINER_NAME 2>/dev/null || true
    echo -e "${GREEN}✅ Cleanup complete${NC}"
}
trap cleanup EXIT

# Test the server
echo -e "${GREEN}=== Running Tests ===${NC}"
echo ""

# Test 1: Container health
echo "Test 1: Container health"
if docker ps | grep -q $CONTAINER_NAME; then
    echo -e "${GREEN}✅ Container is healthy${NC}"
else
    echo -e "${RED}❌ Container is not running${NC}"
fi
echo ""

# Test 2: Server responds
echo "Test 2: Server responds on port $PORT"
if curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/health | grep -q "200\|404"; then
    echo -e "${GREEN}✅ Server responds${NC}"
else
    echo -e "${RED}❌ Server not responding${NC}"
    echo "Container logs:"
    docker logs $CONTAINER_NAME
fi
echo ""

# Test 3: Authentication (if key is set)
if [ -n "$TEST_KEY" ]; then
    echo "Test 3: Authentication"

    # Without key (should fail)
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/mcp/tools)
    if [ "$HTTP_CODE" = "401" ]; then
        echo -e "${GREEN}✅ Rejects requests without API key${NC}"
    else
        echo -e "${YELLOW}⚠️  Expected 401, got $HTTP_CODE (auth might be disabled)${NC}"
    fi

    # With key (should succeed)
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $TEST_KEY" \
        http://localhost:$PORT/mcp/tools)
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
        echo -e "${GREEN}✅ Accepts requests with valid API key${NC}"
    else
        echo -e "${YELLOW}⚠️  Expected 200/204, got $HTTP_CODE${NC}"
    fi
else
    echo "Test 3: Skipped (no API key configured)"
fi
echo ""

# Show container info
echo -e "${GREEN}=== Container Info ===${NC}"
echo "Name:    $CONTAINER_NAME"
echo "Image:   $IMAGE_NAME"
echo "Port:    localhost:$PORT"
echo ""
echo "View logs:"
echo "  docker logs $CONTAINER_NAME"
echo ""
echo "Access server:"
echo "  curl http://localhost:$PORT/health"
if [ -n "$TEST_KEY" ]; then
    echo "  curl -H \"Authorization: Bearer $TEST_KEY\" http://localhost:$PORT/mcp/tools"
fi
echo ""

# Keep container running option
read -p "Keep container running? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    trap - EXIT  # Disable cleanup
    echo -e "${GREEN}Container is still running. Stop it with:${NC}"
    echo "  docker stop $CONTAINER_NAME"
    echo "  docker rm $CONTAINER_NAME"
else
    echo -e "${YELLOW}Stopping container...${NC}"
fi
