"""Tool registration entrypoints."""

from __future__ import annotations

from typing import Protocol


class ToolRegistrar(Protocol):
    """Protocol describing the subset of FastMCP used by our tools."""

    def tool(self, *args, **kwargs):  # type: ignore[override]
        ...


def register_all_tools(server: ToolRegistrar) -> None:
    from .properties import register_property_tools
    from .tenants import register_tenant_tools
    from .transactions import register_transaction_tools

    register_property_tools(server)
    register_tenant_tools(server)
    register_transaction_tools(server)
