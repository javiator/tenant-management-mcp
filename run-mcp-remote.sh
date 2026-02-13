#!/bin/bash
set -euo pipefail

# Critical for SSH: Change to the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Try to find uv in common locations if not in PATH
UV_BIN=$(which uv 2>/dev/null || echo "/home/javiator/.local/bin/uv")

# Load .env file if it exists
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Configuration
DEFAULT_URL="http://localhost:8000/sse"
MCP_REMOTE_URL="${MCP_REMOTE_URL:-$DEFAULT_URL}"
MCP_API_KEY="${MCP_API_KEY:-}"
MCP_REMOTE_TRANSPORT="${MCP_REMOTE_TRANSPORT:-sse}"
HTTPX_TIMEOUT="${HTTPX_TIMEOUT:-30}"

# Override defaults with positional arguments
if [ $# -ge 1 ]; then
    if [[ "$1" == "-h" || "$1" == "--help" ]]; then
        echo "Usage: $0 [url] [api_key] [transport]" >&2
        exit 0
    fi
    MCP_REMOTE_URL="$1"
    shift
fi

if [ $# -ge 1 ]; then
    MCP_API_KEY="$1"
    shift
fi

if [ $# -ge 1 ]; then
    MCP_REMOTE_TRANSPORT="$1"
    shift
fi

if [ -z "$MCP_API_KEY" ]; then
    echo "Error: MCP_API_KEY is not set." >&2
    exit 1
fi

# Redirect all info to stderr
echo "Starting mcp-proxy..." >&2
echo "Connecting to: $MCP_REMOTE_URL (Transport: $MCP_REMOTE_TRANSPORT)" >&2

# Use --quiet and --no-progress to ensure NO output on stdout except MCP JSON
# We set HTTPX_TIMEOUT environment variable in case the library respects it,
# though mcp-proxy might need its own timeout flag if it existed.
export HTTPX_TIMEOUT
exec "$UV_BIN" run --quiet --no-progress mcp-proxy \
    --transport "$MCP_REMOTE_TRANSPORT" \
    --headers Authorization "Bearer $MCP_API_KEY" \
    "$MCP_REMOTE_URL" "$@"
