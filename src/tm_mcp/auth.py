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

    Non-MCP paths (health checks, etc.) pass through without authentication.
    The 401 response is a plain JSON body — no ``WWW-Authenticate`` OAuth
    challenge, so MCP clients won't attempt an OAuth discovery flow.
    """

    def __init__(self, app: ASGIApp, *, allowed_tokens: Set[str]) -> None:
        self.app = app
        self._allowed_tokens = allowed_tokens

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)

        # Only protect the /mcp endpoint
        if not request.url.path.startswith("/mcp"):
            await self.app(scope, receive, send)
            return

        auth_header = request.headers.get("authorization", "")
        if not auth_header.lower().startswith("bearer "):
            await self._send_error(
                send,
                status_code=401,
                message="Missing bearer token. Provide Authorization: Bearer <token> header.",
            )
            return

        token = auth_header[7:]
        if token not in self._allowed_tokens:
            await self._send_error(
                send,
                status_code=401,
                message="Invalid bearer token.",
            )
            return

        await self.app(scope, receive, send)

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
