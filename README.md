# TM MCP Server (Python / uv)

Python implementation of the Model Context Protocol (MCP) server that mirrors the Tenant Management backend REST API. Built with the `mcp` library’s FastMCP server plus `pydantic` and `httpx`, this project converts every backend capability into agent-friendly MCP tools.

Use this server whenever an agentic workflow needs CRUD access to properties, tenants, or transactions without re-implementing HTTP plumbing.

## Prerequisites

- Python 3.11 or newer
- [`uv`](https://github.com/astral-sh/uv) for dependency and virtual environment management
- Tenant Management backend reachable at `BACKEND_MCP_BASE_URL` (defaults to `http://localhost:8080`)

## Quick Start

```bash
cd tenant-management-mcp
cp .env.example .env                       # adjust configuration
uv sync                                    # install dependencies
# Default (stdio transport) for MCP clients
uv run tm-mcp

# Or serve over HTTP for manual testing
uv run tm-mcp --transport streamable-http --host 0.0.0.0 --port 8000
```

> **Note:** The default `stdio` transport is designed for MCP-compatible clients that spawn the
> server as a child process. Use the `streamable-http` transport when you need a long-running server
> for manual testing or remote deployments.

During development you can also run `uv run python -m tm_mcp` or attach a debugger to the module entry point.

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `BACKEND_MCP_BASE_URL` | Base URL of the Spring Boot backend REST API. Trailing slashes are stripped automatically. | `http://localhost:8080` |
| `BACKEND_MCP_API_TOKEN` | Optional bearer token for authenticated deployments. | _unset_ |
| `MCP_API_KEYS` | Comma-separated list of bearer tokens for client authentication via `Authorization: Bearer` header. Leave empty to disable authentication (development mode). | _unset_ |

Configuration is parsed through `pydantic` on startup; misconfigurations raise descriptive errors immediately.

## Authentication

The MCP server supports bearer token authentication to secure access to your tenant management data. Clients authenticate via the standard `Authorization: Bearer <token>` header.

**Quick Start:**
```bash
# Generate API keys
uv run python scripts/manage_keys.py generate --name "Your Name"

# Configure authentication
export MCP_API_KEYS="mcp_key1,mcp_key2,mcp_key3"

# Start authenticated server
uv run tm-mcp --transport streamable-http
```

**Documentation:**
- [Authentication Guide](docs/AUTHENTICATION.md) - Complete authentication setup and usage
- [Key Management Guide](docs/KEY_MANAGEMENT.md) - Managing API keys
- [Quick Start: Keys](docs/QUICK_START_KEYS.md) - 5-minute quick start

**Note:** Authentication is only enforced on HTTP transports (`streamable-http`). Leave `MCP_API_KEYS` empty for local development without authentication.

## Tool Catalogue

All tools return JSON-friendly data structures unless noted. Dates are represented as ISO 8601 strings (e.g., `2025-01-05`).

### Property Tools

| Tool | Purpose | Input Shape |
|------|---------|-------------|
| `list_properties` | Fetch every property managed by the backend. | _none_ |
| `get_property` | Load a property by identifier. | `{ "property_id": number }` |
| `create_property` | Create a property. | `{ "address": string, "rent": number, "maintenance": number }` |
| `update_property` | Update a property (full payload required). | `{ "id": number, "address": string, "rent": number, "maintenance": number }` |
| `delete_property` | Delete a property. Returns a confirmation string. | `{ "property_id": number }` |
| `list_property_transactions` | Retrieve transactions for a property. | `{ "property_id": number }` |

Example usage:

```jsonc
{
  "tool": "create_property",
  "input": {
    "address": "400 Market Street, Unit 9",
    "rent": 1800,
    "maintenance": 150
  }
}
```

### Tenant Tools

| Tool | Purpose | Input Shape |
|------|---------|-------------|
| `list_tenants` | Fetch all tenants (includes linked property info). | _none_ |
| `get_tenant` | Load a tenant by identifier. | `{ "tenant_id": number }` |
| `create_tenant` | Create a tenant. Requires `name` and `propertyId`. | `{ "name": string, "propertyId": number, ...optional fields }` |
| `update_tenant` | Update one or more tenant fields. | `{ "id": number, ...at least one field }` |
| `delete_tenant` | Delete a tenant. Returns a confirmation string. | `{ "tenant_id": number }` |
| `list_tenant_transactions` | Retrieve all transactions for a tenant. | `{ "tenant_id": number }` |

Optional tenant fields include passport metadata, contact numbers, rent/security, and contract dates. Provide `null` to clear a field.

### Transaction Tools

| Tool | Purpose | Input Shape |
|------|---------|-------------|
| `list_transactions` | Fetch every transaction. | _none_ |
| `get_transaction` | Load a transaction by identifier. | `{ "transaction_id": number }` |
| `create_transaction` | Create a transaction. Requires `propertyId`, `type`, `amount`, and `transactionDate`. | `{ "propertyId": number, "type": string, "amount": number, "transactionDate": string, ...optional }` |
| `update_transaction` | Update one or more transaction fields. | `{ "id": number, ...at least one field }` |
| `delete_transaction` | Delete a transaction. Returns a confirmation string. | `{ "transaction_id": number }` |

**Payment categorisation:** Any transaction type other than `payment_received` represents an outstanding charge. Entries tagged `payment_received` record money collected from the tenant, so MCP clients should subtract them when summarising balances.

**Allowed `type` values:** `rent`, `security`, `payment_received`, `gas`, `electricity`, `water`, `maintenance`, `misc`

## Error Handling

- Non-2xx backend responses raise `BackendApiError` with HTTP status codes and backend-supplied details.
- Invalid or unexpected backend payloads surface as validation errors, making it obvious when API contracts drift.
- Connectivity issues surface immediately so orchestrators can retry or escalate.

## Development Notes

- Tool code lives in `src/tm_mcp/tools/` and should stay thin—validate input, invoke the backend, return typed data.
- `schemas.py` centralizes all `pydantic` models. Update it before changing tool behavior.
- `http_client.py` encapsulates HTTP concerns (timeouts, auth headers, error handling). Extend it if retry logic or logging is needed.
- Lint with `uv run ruff check .` and add tests with `uv run pytest`.

## Extending the Server

1. Add or update schemas in `schemas.py`.
2. Implement new tool logic under `tools/`.
3. Register the tool during server construction if you add a new module.
4. Document the tool in this README and share sample inputs/outputs.

## MCP Client Integration

Run the server with `uv run tm-mcp` and configure your MCP-compatible client (e.g., Cursor MCP, Claude Desktop) to point at the resulting socket or transport endpoint. Refer to your client’s documentation for wiring internal MCP servers.
