"""Authentication middleware for the MCP server."""

from __future__ import annotations

import os
from typing import Optional, Set

from mcp.server.fastmcp import Context


class AuthenticationError(Exception):
    """Raised when bearer token authentication fails."""

    pass


# Backward compatibility alias
ApiKeyAuthError = AuthenticationError


class BearerTokenValidator:
    """Validates bearer tokens against configured allowed tokens."""

    def __init__(self) -> None:
        """Initialize the validator with tokens from environment."""
        self._allowed_tokens = self._load_tokens_from_env()

    def _load_tokens_from_env(self) -> Set[str]:
        """Load allowed tokens from MCP_API_KEYS environment variable."""
        keys_str = os.environ.get("MCP_API_KEYS", "")
        if not keys_str:
            return set()

        # Split by comma and strip whitespace
        tokens = {token.strip() for token in keys_str.split(",") if token.strip()}
        return tokens

    def is_authentication_enabled(self) -> bool:
        """Check if authentication is enabled (i.e., tokens are configured)."""
        return len(self._allowed_tokens) > 0

    def validate_token(self, token: Optional[str]) -> bool:
        """
        Validate a bearer token.

        Args:
            token: The bearer token to validate

        Returns:
            True if valid, False otherwise
        """
        if not self.is_authentication_enabled():
            # No tokens configured = authentication disabled (development mode)
            return True

        if not token:
            return False

        return token in self._allowed_tokens

    def require_valid_token(self, token: Optional[str]) -> None:
        """
        Validate a bearer token and raise an exception if invalid.

        Args:
            token: The bearer token to validate

        Raises:
            AuthenticationError: If the token is invalid or missing
        """
        if not self.validate_token(token):
            if not self.is_authentication_enabled():
                # Should never happen, but just in case
                return

            if not token:
                raise AuthenticationError(
                    "Missing bearer token. Provide Authorization: Bearer <token> header."
                )
            else:
                raise AuthenticationError("Invalid bearer token.")


# Backward compatibility alias
ApiKeyValidator = BearerTokenValidator

# Global validator instance
_validator: Optional[BearerTokenValidator] = None


def get_validator() -> BearerTokenValidator:
    """Get the global bearer token validator instance."""
    global _validator
    if _validator is None:
        _validator = BearerTokenValidator()
    return _validator


def validate_request(context: Context) -> None:
    """
    Validate the bearer token from the request context.

    This function should be called at the beginning of each tool handler
    to ensure the request is authenticated.

    Args:
        context: The MCP request context

    Raises:
        AuthenticationError: If authentication fails
    """
    validator = get_validator()

    # Extract bearer token from context metadata/headers
    # FastMCP passes headers in context.metadata
    token = None
    if hasattr(context, "metadata") and context.metadata:
        auth_header = (
            context.metadata.get("authorization")
            or context.metadata.get("Authorization")
        )

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix

    validator.require_valid_token(token)
