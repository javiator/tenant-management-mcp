"""Authentication for the MCP server.

Provides transparent bearer token validation that checks for tokens in the
request context without triggering interactive CLI auth prompts.
"""

from __future__ import annotations

import functools
import os
from typing import Any, Callable, Optional, Set, TypeVar

from mcp.server.fastmcp import Context

T = TypeVar("T", bound=Callable[..., Any])


class AuthenticationError(Exception):
    """Raised when bearer token authentication fails."""

    pass


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
        """Validate a bearer token."""
        if not self.is_authentication_enabled():
            return True

        if not token:
            return False

        return token in self._allowed_tokens


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

    Args:
        context: The MCP request context

    Raises:
        AuthenticationError: If authentication fails
    """
    validator = get_validator()
    if not validator.is_authentication_enabled():
        return

    # FastMCP passes headers in context.metadata
    token = None
    if hasattr(context, "metadata") and context.metadata:
        # Check both cases just in case
        auth_header = (
            context.metadata.get("authorization")
            or context.metadata.get("Authorization")
        )

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix

    if not validator.validate_token(token):
        if not token:
            raise AuthenticationError(
                "Missing bearer token. Provide Authorization: Bearer <token> header."
            )
        else:
            raise AuthenticationError("Invalid bearer token.")


def authenticated(f: T) -> T:
    """
    Decorator to enforce bearer token authentication on a tool.

    The tool function must accept a 'context: Context' argument.
    """

    @functools.wraps(f)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        context = kwargs.get("context")
        if not isinstance(context, Context):
            # Try to find it in args if not in kwargs
            for arg in args:
                if isinstance(arg, Context):
                    context = arg
                    break

        if isinstance(context, Context):
            validate_request(context)
        elif get_validator().is_authentication_enabled():
            # If auth is enabled but no context was provided to the tool,
            # we can't verify, so we must fail safely.
            raise AuthenticationError("Internal error: Tool context missing for authentication.")

        return await f(*args, **kwargs)

    return wrapper  # type: ignore


# Backward compatibility aliases
McpBearerTokenVerifier = BearerTokenValidator
ApiKeyValidator = BearerTokenValidator

