"""Authentication middleware for the MCP server."""

from __future__ import annotations

import os
from typing import Optional, Set

from mcp.server.fastmcp import Context


class ApiKeyAuthError(Exception):
    """Raised when API key authentication fails."""

    pass


class ApiKeyValidator:
    """Validates API keys against configured allowed keys."""

    def __init__(self) -> None:
        """Initialize the validator with keys from environment."""
        self._allowed_keys = self._load_keys_from_env()

    def _load_keys_from_env(self) -> Set[str]:
        """Load allowed API keys from MCP_API_KEYS environment variable."""
        keys_str = os.environ.get("MCP_API_KEYS", "")
        if not keys_str:
            return set()

        # Split by comma and strip whitespace
        keys = {key.strip() for key in keys_str.split(",") if key.strip()}
        return keys

    def is_authentication_enabled(self) -> bool:
        """Check if authentication is enabled (i.e., keys are configured)."""
        return len(self._allowed_keys) > 0

    def validate_key(self, api_key: Optional[str]) -> bool:
        """
        Validate an API key.

        Args:
            api_key: The API key to validate

        Returns:
            True if valid, False otherwise
        """
        if not self.is_authentication_enabled():
            # No keys configured = authentication disabled (development mode)
            return True

        if not api_key:
            return False

        return api_key in self._allowed_keys

    def require_valid_key(self, api_key: Optional[str]) -> None:
        """
        Validate an API key and raise an exception if invalid.

        Args:
            api_key: The API key to validate

        Raises:
            ApiKeyAuthError: If the key is invalid or missing
        """
        if not self.validate_key(api_key):
            if not self.is_authentication_enabled():
                # Should never happen, but just in case
                return

            if not api_key:
                raise ApiKeyAuthError("Missing API key. Provide X-API-Key header.")
            else:
                raise ApiKeyAuthError("Invalid API key.")


# Global validator instance
_validator: Optional[ApiKeyValidator] = None


def get_validator() -> ApiKeyValidator:
    """Get the global API key validator instance."""
    global _validator
    if _validator is None:
        _validator = ApiKeyValidator()
    return _validator


def validate_request(context: Context) -> None:
    """
    Validate the API key from the request context.

    This function should be called at the beginning of each tool handler
    to ensure the request is authenticated.

    Args:
        context: The MCP request context

    Raises:
        ApiKeyAuthError: If authentication fails
    """
    validator = get_validator()

    # Extract API key from context metadata/headers
    # FastMCP passes headers in context.metadata
    api_key = None
    if hasattr(context, "metadata") and context.metadata:
        # Try common header names
        api_key = (
            context.metadata.get("x-api-key")
            or context.metadata.get("X-API-Key")
            or context.metadata.get("authorization")
        )

        # If authorization header, extract bearer token
        if api_key and api_key.startswith("Bearer "):
            api_key = api_key[7:]  # Remove "Bearer " prefix

    validator.require_valid_key(api_key)
