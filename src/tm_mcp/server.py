"""Server factory for the Tenant Management MCP service."""

from __future__ import annotations

import logging

from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

from .auth import McpBearerTokenVerifier
from .tools import register_all_tools

logger = logging.getLogger(__name__)


def build_server(*, host: str | None = None, port: int | None = None) -> FastMCP:
    """Configure the MCP server with all registered tools."""

    verifier = McpBearerTokenVerifier()

    # When tokens are configured, enable FastMCP's built-in bearer auth
    # so the SDK's BearerAuthBackend + RequireAuthMiddleware enforce
    # Authorization: Bearer on every MCP route automatically.
    auth_kwargs: dict = {}
    if verifier.is_authentication_enabled():
        logger.info(
            "Bearer token authentication enabled with %d configured tokens",
            verifier.token_count,
        )
        auth_kwargs["token_verifier"] = verifier
        auth_kwargs["auth"] = AuthSettings(
            issuer_url="https://auth.placeholder.local",
            resource_server_url=None,
        )
    else:
        logger.warning(
            "Authentication DISABLED - no bearer tokens configured. "
            "Set MCP_API_KEYS environment variable to enable authentication."
        )

    server = FastMCP(
        name="tenant-management-mcp",
        instructions="Expose the Tenant Management backend REST API as MCP tools.",
        host=host or "127.0.0.1",
        port=port or 8000,
        **auth_kwargs,
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
    server.run(transport=transport, mount_path=mount_path)
