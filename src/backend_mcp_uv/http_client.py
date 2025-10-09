"""HTTP client helpers wrapping the Tenant Management backend."""

from __future__ import annotations

import json
from typing import Any, Dict, Mapping, Optional, TypeVar

import httpx
from pydantic import TypeAdapter, ValidationError

from .config import settings

T = TypeVar("T")


class BackendApiError(Exception):
    """Raised when the backend returns a non-successful response."""

    def __init__(
        self,
        status_code: int,
        message: str,
        *,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details


async def _send(
    method: str,
    path: str,
    *,
    params: Optional[Mapping[str, Any]] = None,
    body: Optional[Any] = None,
) -> httpx.Response:
    """Send an HTTP request to the backend and raise `BackendApiError` on failure."""
    headers: Dict[str, str] = {
        "Accept": "application/json",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    if settings.api_token:
        headers["Authorization"] = f"Bearer {settings.api_token}"

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        timeout=httpx.Timeout(15.0),
        headers=headers,
    ) as client:
        response = await client.request(method, path, params=params, json=body)

    if response.is_error:
        try:
            details = response.json()
        except ValueError:
            details = response.text
        message = (
            details
            if isinstance(details, str) and details.strip()
            else response.reason_phrase or "Backend API request failed"
        )
        raise BackendApiError(response.status_code, message, details=details)

    return response


async def request_json(
    method: str,
    path: str,
    *,
    params: Optional[Mapping[str, Any]] = None,
    body: Optional[Any] = None,
    adapter: TypeAdapter[T],
) -> T:
    """Send a request and parse the JSON body with the provided type adapter."""
    response = await _send(method, path, params=params, body=body)

    if response.status_code == httpx.codes.NO_CONTENT:
        raise BackendApiError(
            500,
            "Backend returned no content but a JSON payload was expected.",
        )

    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        raise BackendApiError(
            response.status_code,
            "Backend returned an invalid JSON payload.",
            details=response.text,
        ) from exc

    try:
        return adapter.validate_python(payload)
    except ValidationError as exc:
        raise BackendApiError(
            response.status_code,
            "Backend response validation failed.",
            details={"errors": exc.errors(), "payload": payload},
        ) from exc


async def request_void(
    method: str,
    path: str,
    *,
    params: Optional[Mapping[str, Any]] = None,
    body: Optional[Any] = None,
) -> None:
    """Send a request where the response body is not required."""
    await _send(method, path, params=params, body=body)
