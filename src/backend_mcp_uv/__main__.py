"""Entry point for running the MCP server via `python -m backend_mcp_uv`."""

from __future__ import annotations

import argparse

from .server import run

TRANSPORT_CHOICES = ("stdio", "sse", "streamable-http")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Launch the Tenant Management MCP server. "
            "Defaults to stdio transport for MCP-compatible clients."
        )
    )
    parser.add_argument(
        "--transport",
        choices=TRANSPORT_CHOICES,
        default="stdio",
        help="Transport to expose (stdio, sse, or streamable-http).",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Host/interface to bind when using SSE or streamable-http transports.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind when using SSE or streamable-http transports.",
    )
    parser.add_argument(
        "--mount-path",
        default=None,
        help="Optional mount path when using the SSE transport.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    run(
        transport=args.transport,
        host=args.host,
        port=args.port,
        mount_path=args.mount_path,
    )


if __name__ == "__main__":
    main()
