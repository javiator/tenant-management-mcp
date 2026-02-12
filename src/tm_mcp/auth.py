"""Bearer token authentication for the MCP server.

Implements the MCP SDK's TokenVerifier protocol so that FastMCP's built-in
BearerAuthBackend and RequireAuthMiddleware enforce ``Authorization: Bearer``
on every MCP route automatically.
"""

from __future__ import annotations

import logging
import os
from typing import Optional, Set

from mcp.server.auth.provider import AccessToken

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when bearer token authentication fails."""

    pass


# Backward compatibility alias
ApiKeyAuthError = AuthenticationError


def _load_tokens_from_env() -> Set[str]:
    """Load allowed tokens from the MCP_API_KEYS environment variable."""
    keys_str = os.environ.get("MCP_API_KEYS", "")
    if not keys_str:
        return set()
    return {t.strip() for t in keys_str.split(",") if t.strip()}


class McpBearerTokenVerifier:
    """Implements the MCP SDK ``TokenVerifier`` protocol.

    FastMCP calls ``verify_token(token)`` for every inbound HTTP request
    that carries an ``Authorization: Bearer <token>`` header.  Returning an
    ``AccessToken`` means "allow"; returning ``None`` means "reject with 401".
    """

    def __init__(self) -> None:
        self._allowed_tokens = _load_tokens_from_env()

    @property
    def token_count(self) -> int:
        return len(self._allowed_tokens)

    def is_authentication_enabled(self) -> bool:
        return self.token_count > 0

    async def verify_token(self, token: str) -> Optional[AccessToken]:
        """Verify a bearer token against the configured allow-list.

        Returns an ``AccessToken`` on success or ``None`` on failure.
        """
        if token in self._allowed_tokens:
            return AccessToken(
                token=token,
                client_id="mcp-client",
                scopes=[],
            )
        return None


# Keep the old name around so existing imports don't break.
BearerTokenValidator = McpBearerTokenVerifier
ApiKeyValidator = McpBearerTokenVerifier
