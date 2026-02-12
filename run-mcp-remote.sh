#!/bin/bash
set -euo pipefail

# Load .env file if it exists (robust way)
if [ -f .env ]; then
    # Use set -a to export all variables defined in the sourced file
    set -a
    source .env
    set +a
fi

# Configuration
DEFAULT_URL="http://localhost:8000/sse"
MCP_REMOTE_URL="${MCP_REMOTE_URL:-$DEFAULT_URL}"
MCP_API_KEY="${MCP_API_KEY:-}"
DEBUG="${DEBUG:-false}"

# Usage help
usage() {
    echo "Usage: $0 [url] [api_key]" >&2
    echo "" >&2
    echo "Arguments:" >&2
    echo "  url      The full path to the remote MCP SSE endpoint (default: $MCP_REMOTE_URL)" >&2
    echo "  api_key  The API key for authentication (default: value of MCP_API_KEY env var)" >&2
    echo "" >&2
    echo "Options:" >&2
    echo "  DEBUG=true $0 ...  Print the final command instead of executing" >&2
}

# Override defaults with positional arguments
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
    echo "Error: MCP_API_KEY is not set." >&2
    echo "Please set it in .env, as an environment variable, or pass as the second argument." >&2
    echo "" >&2
    usage
    exit 1
fi

if [ "$DEBUG" = "true" ]; then
    echo "--- DEBUG MODE ---" >&2
    echo "Remote URL: $MCP_REMOTE_URL" >&2
    echo "Auth Header: X-API-Key: $MCP_API_KEY" >&2
    echo "Command: uv run mcp-proxy --headers X-API-Key \"$MCP_API_KEY\" \"$MCP_REMOTE_URL\" $@" >&2
    exit 0
fi

# Redirect info to stderr
echo "Starting mcp-proxy..." >&2
echo "Connecting to: $MCP_REMOTE_URL" >&2

# Use --quiet to prevent uv from printing to stdout/stderr unless there's an error
exec uv run --quiet mcp-proxy \
    --headers X-API-Key "$MCP_API_KEY" \
    "$MCP_REMOTE_URL" "$@"
