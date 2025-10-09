"""Server factory for the Tenant Management MCP service."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .tools import register_all_tools


def build_server(*, host: str | None = None, port: int | None = None) -> FastMCP:
    """Configure the MCP server with all registered tools."""
    server = FastMCP(
        name="tenant-management-backend-mcp-uv",
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
    """Run the MCP server."""
    server = build_server(host=host, port=port)
    server.run(transport=transport, mount_path=mount_path)
