#!/bin/bash
set -euo pipefail

# Load .env file if it exists
if [ -f .env ]; then
    # Load variables while ignoring comments
    export $(grep -v '^#' .env | xargs)
fi

# Configuration
# Can be overridden by environment variables
DEFAULT_URL="http://localhost:8000/sse"
MCP_REMOTE_URL="${MCP_REMOTE_URL:-$DEFAULT_URL}"
MCP_API_KEY="${MCP_API_KEY:-}"

# Usage help
usage() {
    echo "Usage: $0 [url] [api_key]"
    echo ""
    echo "Arguments:"
    echo "  url      The full path to the remote MCP SSE endpoint (default: $MCP_REMOTE_URL)"
    echo "  api_key  The API key for authentication (default: value of MCP_API_KEY env var)"
    echo ""
    echo "Example:"
    echo "  $0 https://remote-mcp.example.com/sse my-secret-key"
}

# Override defaults with positional arguments if provided
if [ $# -ge 1 ]; then
    if [[ "$1" == "-h" || "$1" == "--help" ]]; then
        usage
        exit 0
    fi
    MCP_REMOTE_URL="$1"
    shift
fi

if [ $# -ge 1 ]; then
    MCP_API_KEY="$1"
    shift
fi

if [ -z "$MCP_API_KEY" ]; then
    echo "Error: MCP_API_KEY is not set. Please provide it as an argument or set the environment variable."
    echo ""
    usage
    exit 1
fi

echo "Starting mcp-proxy..."
echo "Remote URL: $MCP_REMOTE_URL"
echo "Auth Header: X-API-Key: ${MCP_API_KEY:0:5}..."

# Execute mcp-proxy
# Any additional arguments passed to this script will be forwarded to mcp-proxy
exec uv run mcp-proxy \
    --headers X-API-Key "$MCP_API_KEY" \
    "$MCP_REMOTE_URL" "$@"
