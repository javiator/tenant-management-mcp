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
        env_prefix="BACKEND_MCP_",
        case_sensitive=False,
    )

    base_url: AnyHttpUrl = Field(
        default="http://localhost:8080",
        description="Base URL for the Tenant Management backend REST API.",
    )
    api_token: Optional[str] = Field(
        default=None,
        description="Optional bearer token shared with the backend for authenticated requests.",
    )

    @field_validator("base_url")
    @classmethod
    def normalize_base_url(cls, value: AnyHttpUrl) -> str:
        """Return the base URL as a string without trailing slashes."""
        return str(value).rstrip("/")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cache settings so they are instantiated exactly once."""
    return Settings()


settings = get_settings()
