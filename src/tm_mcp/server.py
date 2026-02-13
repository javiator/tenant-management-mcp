"""Server factory for the Tenant Management MCP service."""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from .auth import BearerTokenMiddleware, get_allowed_tokens, is_authentication_enabled
from .tools import register_all_tools

logger = logging.getLogger(__name__)


def build_server(*, host: str | None = None, port: int | None = None) -> FastMCP:
    """Configure the MCP server with all registered tools (no auth wired yet)."""
    server = FastMCP(
        name="tenant-management-mcp",
        instructions="Expose the Tenant Management backend REST API as MCP tools.",
        host=host or "127.0.0.1",
        port=port or 8000,
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
    """Run the MCP server.

    For HTTP transports (streamable-http, sse), the bearer-token middleware
    is added as a plain ASGI wrapper around FastMCP's Starlette app — no SDK
    OAuth machinery, so clients like Gemini won't attempt an OAuth flow.
    """
    server = build_server(host=host, port=port)

    if transport == "stdio":
        # stdio has no HTTP headers; auth is handled by the parent process
        server.run(transport="stdio")
        return

    # ---------- HTTP transports: add bearer-token middleware ----------
    import anyio
    import uvicorn

    # Build the Starlette app from FastMCP
    if transport == "streamable-http":
        starlette_app = server.streamable_http_app()
    elif transport == "sse":
        starlette_app = server.sse_app(mount_path)
    else:
        raise ValueError(f"Unknown transport: {transport}")

    # Add a health check endpoint
    from starlette.responses import JSONResponse
    
    @starlette_app.route("/health")
    async def health(request):
        return JSONResponse({"status": "ok"})

    # Wrap with bearer-token middleware when tokens are configured
    if is_authentication_enabled():
        allowed_tokens = get_allowed_tokens()
        logger.info(
            "Bearer token authentication enabled with %d configured tokens",
            len(allowed_tokens),
        )
        starlette_app = BearerTokenMiddleware(
            starlette_app,
            allowed_tokens=allowed_tokens,
        )
    else:
        logger.warning(
            "Authentication DISABLED - no bearer tokens configured. "
            "Set MCP_API_KEYS environment variable to enable authentication."
        )

    config = uvicorn.Config(
        starlette_app,
        host=server.settings.host,
        port=server.settings.port,
        log_level=server.settings.log_level.lower(),
    )

    async def _serve() -> None:
        srv = uvicorn.Server(config)
        await srv.serve()

    anyio.run(_serve)
