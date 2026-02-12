"""Server factory for the Tenant Management MCP service."""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from .auth import BearerTokenValidator
from .tools import register_all_tools

logger = logging.getLogger(__name__)


def build_server(*, host: str | None = None, port: int | None = None) -> FastMCP:
    """Configure the MCP server with all registered tools."""
    server = FastMCP(
        name="tenant-management-mcp",
        instructions="Expose the Tenant Management backend REST API as MCP tools.",
        host=host or "127.0.0.1",
        port=port or 8000,
    )

    # Initialize authentication validator
    validator = BearerTokenValidator()
    if validator.is_authentication_enabled():
        logger.info(
            "Bearer token authentication enabled with %d configured tokens",
            len(validator._allowed_tokens),
        )
    else:
        logger.warning(
            "Authentication DISABLED - no bearer tokens configured. "
            "Set MCP_API_KEYS environment variable to enable authentication."
        )

    register_all_tools(server)
    return server


def run(
    *,
    transport: str = "stdio",
    host: str | None = None,
    port: int | None = None,
    mount_path: str | None = None,
) -> None:
    """Run the MCP server."""
    server = build_server(host=host, port=port)

    # Note: For HTTP-based transports, authentication should be handled at the infrastructure level
    # (e.g., Cloud Run with IAP, API Gateway, or reverse proxy like nginx/Caddy with auth middleware)
    # For development without such infrastructure, MCP_API_KEYS check is informational only.
    # In production on Cloud Run, consider using Cloud Run's built-in authentication or a gateway.

    server.run(transport=transport, mount_path=mount_path)
