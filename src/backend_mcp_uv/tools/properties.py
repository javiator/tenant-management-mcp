"""Property-related MCP tool definitions."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, PositiveInt

from ..http_client import request_json, request_void
from ..schemas import (
    Property,
    PropertyInput,
    PropertyUpdate,
    Transaction,
    property_adapter,
    property_list_adapter,
    transaction_list_adapter,
)


def register_property_tools(server) -> None:
    """Register property tools on the provided MCP server."""

    @server.tool(
        name="list_properties",
        description="Retrieve every property managed by the backend.",
    )
    async def list_properties() -> list[Property]:
        return await request_json("GET", "/api/properties", adapter=property_list_adapter)

    @server.tool(name="get_property", description="Fetch a single property by identifier.")
    async def get_property(
        property_id: Annotated[PositiveInt, Field(description="Unique property identifier")],
    ) -> Property:
        return await request_json(
            "GET",
            f"/api/properties/{property_id}",
            adapter=property_adapter,
        )

    @server.tool(
        name="create_property",
        description="Create a property. Requires address, rent, and maintenance amount.",
    )
    async def create_property(payload: PropertyInput) -> Property:
        return await request_json(
            "POST",
            "/api/properties",
            body=payload.model_dump(),
            adapter=property_adapter,
        )

    @server.tool(
        name="update_property",
        description="Update an existing property. Supply the property identifier and full payload.",
    )
    async def update_property(payload: PropertyUpdate) -> Property:
        body = payload.model_dump()
        property_id = body.pop("id")
        return await request_json(
            "PUT",
            f"/api/properties/{property_id}",
            body=body,
            adapter=property_adapter,
        )

    @server.tool(name="delete_property", description="Delete a property by identifier.")
    async def delete_property(
        property_id: Annotated[PositiveInt, Field(description="Unique property identifier")],
    ) -> str:
        await request_void("DELETE", f"/api/properties/{property_id}")
        return f"Property {property_id} deleted successfully."

    @server.tool(
        name="list_property_transactions",
        description="List transactions associated with a property.",
    )
    async def list_property_transactions(
        property_id: Annotated[PositiveInt, Field(description="Unique property identifier")],
    ) -> list[Transaction]:
        return await request_json(
            "GET",
            f"/api/properties/{property_id}/transactions",
            adapter=transaction_list_adapter,
        )
