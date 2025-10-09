"""Tenant-related MCP tool definitions."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, PositiveInt

from ..http_client import request_json, request_void
from ..schemas import (
    Tenant,
    TenantCreate,
    TenantUpdatePayload,
    Transaction,
    tenant_adapter,
    tenant_list_adapter,
    transaction_list_adapter,
)


def register_tenant_tools(server) -> None:
    """Register tenant tools on the provided MCP server."""

    @server.tool(name="list_tenants", description="Retrieve all tenants managed by the backend.")
    async def list_tenants() -> list[Tenant]:
        return await request_json("GET", "/api/tenants", adapter=tenant_list_adapter)

    @server.tool(name="get_tenant", description="Fetch a single tenant by identifier.")
    async def get_tenant(
        tenant_id: Annotated[PositiveInt, Field(description="Unique tenant identifier")],
    ) -> Tenant:
        return await request_json("GET", f"/api/tenants/{tenant_id}", adapter=tenant_adapter)

    @server.tool(
        name="create_tenant",
        description="Create a tenant. Requires the tenant name and associated property identifier.",
    )
    async def create_tenant(payload: TenantCreate) -> Tenant:
        return await request_json(
            "POST",
            "/api/tenants",
            body=payload.model_dump(exclude_none=True),
            adapter=tenant_adapter,
        )

    @server.tool(
        name="update_tenant",
        description="Update a tenant by identifier. Provide at least one field to change.",
    )
    async def update_tenant(payload: TenantUpdatePayload) -> Tenant:
        body = payload.model_dump(exclude_none=True)
        tenant_id = body.pop("id")
        return await request_json(
            "PUT",
            f"/api/tenants/{tenant_id}",
            body=body,
            adapter=tenant_adapter,
        )

    @server.tool(name="delete_tenant", description="Delete a tenant by identifier.")
    async def delete_tenant(
        tenant_id: Annotated[PositiveInt, Field(description="Unique tenant identifier")],
    ) -> str:
        await request_void("DELETE", f"/api/tenants/{tenant_id}")
        return f"Tenant {tenant_id} deleted successfully."

    @server.tool(
        name="list_tenant_transactions",
        description="List transactions recorded for a tenant.",
    )
    async def list_tenant_transactions(
        tenant_id: Annotated[PositiveInt, Field(description="Unique tenant identifier")],
    ) -> list[Transaction]:
        return await request_json(
            "GET",
            f"/api/tenants/{tenant_id}/transactions",
            adapter=transaction_list_adapter,
        )
