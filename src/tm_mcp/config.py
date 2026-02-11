"""Environment configuration for the Python MCP server."""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration sourced from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env",),
        case_sensitive=False,
    )

    # Backend API settings
    backend_mcp_base_url: AnyHttpUrl = Field(
        default="http://localhost:8080",
        description="Base URL for the Tenant Management backend REST API.",
    )
    backend_mcp_api_token: Optional[str] = Field(
        default=None,
        description="Optional bearer token shared with the backend for authenticated requests.",
    )

    # MCP Server authentication
    mcp_api_keys: str = Field(
        default="",
        description="Comma-separated list of valid API keys for MCP client authentication.",
    )

    @field_validator("backend_mcp_base_url")
    @classmethod
    def normalize_base_url(cls, value: AnyHttpUrl) -> str:
        """Return the base URL as a string without trailing slashes."""
        return str(value).rstrip("/")

    # Backward compatibility properties
    @property
    def base_url(self) -> str:
        """Backward compatible property for base_url."""
        return self.backend_mcp_base_url

    @property
    def api_token(self) -> Optional[str]:
        """Backward compatible property for api_token."""
        return self.backend_mcp_api_token


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cache settings so they are instantiated exactly once."""
    return Settings()


settings = get_settings()
