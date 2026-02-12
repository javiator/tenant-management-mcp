#!/bin/bash
set -euo pipefail

# Critical for SSH: Change to the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

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

# Override defaults with positional arguments
if [ $# -ge 1 ]; then
    if [[ "$1" == "-h" || "$1" == "--help" ]]; then
        echo "Usage: $0 [url] [api_key]" >&2
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
    echo "Error: MCP_API_KEY is not set." >&2
    exit 1
fi

# Redirect all info to stderr
echo "Starting mcp-proxy..." >&2
echo "Connecting to: $MCP_REMOTE_URL" >&2

# Use --quiet and --no-progress to ensure NO output on stdout except MCP JSON
exec uv run --quiet --no-progress mcp-proxy \
    --headers X-API-Key "$MCP_API_KEY" \
    "$MCP_REMOTE_URL" "$@"
