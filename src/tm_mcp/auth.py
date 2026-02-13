"""Bearer token authentication for the MCP server.

Provides a plain Starlette middleware that validates ``Authorization: Bearer``
tokens on MCP routes.  This deliberately avoids the SDK's built-in OAuth auth
machinery (AuthSettings / token_verifier) so that clients like Gemini are not
tricked into starting an OAuth discovery flow — they just send the pre-shared
token and it works.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Set

from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)


def _load_tokens_from_env() -> Set[str]:
    """Load allowed tokens from the MCP_API_KEYS environment variable."""
    keys_str = os.environ.get("MCP_API_KEYS", "")
    if not keys_str:
        return set()
    return {t.strip() for t in keys_str.split(",") if t.strip()}


class BearerTokenMiddleware:
    """ASGI middleware that enforces ``Authorization: Bearer <token>`` on /mcp routes.

    The MCP protocol handshake (``initialize``, ``notifications/initialized``)
    is allowed through without a token so that clients can establish a session
    without being tricked into an OAuth discovery flow.  All other JSON-RPC
    methods (``tools/list``, ``tools/call``, etc.) require a valid bearer token.

    Non-MCP paths (health checks, etc.) pass through without authentication.
    The 401 response is a plain JSON body — no ``WWW-Authenticate`` header — so
    MCP clients won't attempt an OAuth discovery flow.
    """

    # JSON-RPC methods that are allowed without a bearer token.
    _OPEN_METHODS = frozenset({
        "initialize",
        "notifications/initialized",
        "ping",
    })

    def __init__(self, app: ASGIApp, *, allowed_tokens: Set[str]) -> None:
        self.app = app
        self._allowed_tokens = allowed_tokens

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)

        # Non-MCP paths pass through (health checks, etc.)
        if not request.url.path.startswith("/mcp"):
            await self.app(scope, receive, send)
            return

        # If a valid bearer token is present, let everything through.
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:]
            if token in self._allowed_tokens:
                await self.app(scope, receive, send)
                return

        # GET /mcp is the streamable-http notification stream — allow
        # through so the client can receive server-initiated messages.
        if request.method == "GET":
            await self.app(scope, receive, send)
            return

        # For POST requests without a valid token, read the body and check
        # whether the JSON-RPC method is part of the MCP handshake.
        if request.method == "POST":
            body = await self._buffer_body(receive)

            if self._is_open_request(body):
                await self.app(scope, self._replay_receive(body), send)
                return

            # Not an open method and no valid token → reject.
            await self._send_error(
                send,
                status_code=401,
                message="Missing or invalid bearer token. Provide Authorization: Bearer <token> header.",
            )
            return

        # Other HTTP methods — reject.
        await self._send_error(
            send,
            status_code=401,
            message="Missing or invalid bearer token.",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_open_request(self, body: bytes) -> bool:
        """Return True if *body* is a JSON-RPC request whose method(s) are all open."""
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, TypeError):
            return False

        if isinstance(payload, list):
            methods = {m.get("method", "") for m in payload if isinstance(m, dict)}
        elif isinstance(payload, dict):
            methods = {payload.get("method", "")}
        else:
            return False

        return bool(methods) and methods.issubset(self._OPEN_METHODS)

    @staticmethod
    async def _buffer_body(receive: Receive) -> bytes:
        """Read the full request body from the ASGI receive channel."""
        chunks: list[bytes] = []
        while True:
            message = await receive()
            chunk = message.get("body", b"")
            if chunk:
                chunks.append(chunk)
            if not message.get("more_body", False):
                break
        return b"".join(chunks)

    @staticmethod
    def _replay_receive(body: bytes) -> Receive:
        """Return a receive callable that replays a buffered body once."""
        sent = False

        async def _receive() -> dict:
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            # After the body has been replayed, block until disconnect.
            return {"type": "http.disconnect"}

        return _receive

    @staticmethod
    async def _send_error(send: Send, *, status_code: int, message: str) -> None:
        body = json.dumps({"error": "unauthorized", "message": message}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


def is_authentication_enabled() -> bool:
    """Check whether MCP_API_KEYS is configured."""
    return bool(_load_tokens_from_env())


def get_allowed_tokens() -> Set[str]:
    """Return the set of configured bearer tokens."""
    return _load_tokens_from_env()
