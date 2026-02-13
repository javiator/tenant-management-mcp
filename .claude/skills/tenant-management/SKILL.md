---
name: tenant-management
description: >
  Manage rental properties, tenants, and financial transactions via the
  Tenant Management REST API. Use when the user wants to list, create,
  update, delete, or query properties, tenants, or transactions.
user-invocable: true
argument-hint: "<action> e.g. 'list all properties', 'create tenant John for property 1'"
allowed-tools:
  - Bash(.claude/skills/tenant-management/scripts/tm-api.sh *)
---

# Tenant Management API Skill

Use the `tm-api.sh` script for all API operations. The script handles authentication, input validation, response unwrapping, and error formatting. Never use raw `curl` — always go through the script.

**Script path:** `.claude/skills/tenant-management/scripts/tm-api.sh`

## Configuration

The script reads these environment variables automatically:
- `BACKEND_MCP_BASE_URL` (default: `http://localhost:8080`)
- `BACKEND_MCP_API_TOKEN` (optional, added as Bearer token if set)

## Commands

### Properties

| Command | Usage |
|---|---|
| List all | `tm-api.sh list-properties` |
| Get by ID | `tm-api.sh get-property <id>` |
| Create | `tm-api.sh create-property '<json>'` |
| Update | `tm-api.sh update-property <id> '<json>'` |
| Delete | `tm-api.sh delete-property <id>` |
| Transactions | `tm-api.sh list-property-transactions <id>` |

**Create/update body** — all three fields required:
```json
{"address": "123 Main St", "rent": 15000.0, "maintenance": 2000.0}
```

### Tenants

| Command | Usage |
|---|---|
| List all | `tm-api.sh list-tenants` |
| Get by ID | `tm-api.sh get-tenant <id>` |
| Create | `tm-api.sh create-tenant '<json>'` |
| Update | `tm-api.sh update-tenant <id> '<json>'` |
| Delete | `tm-api.sh delete-tenant <id>` |
| Transactions | `tm-api.sh list-tenant-transactions <id>` |

**Create body** — `name` and `propertyId` required, all others optional:
```json
{"name": "John Doe", "propertyId": 1}
```

**Optional fields:** `passport`, `passportValidity`, `aadharNo`, `employmentDetails`, `permanentAddress`, `contactNo`, `emergencyContactNo`, `rent`, `security`, `moveInDate`, `contractStartDate`, `contractExpiryDate`

**Update body** — partial, at least one field:
```json
{"contactNo": "+91-9876543210", "rent": 16000.0}
```

### Transactions

| Command | Usage |
|---|---|
| List all | `tm-api.sh list-transactions` |
| Get by ID | `tm-api.sh get-transaction <id>` |
| Create | `tm-api.sh create-transaction '<json>'` |
| Update | `tm-api.sh update-transaction <id> '<json>'` |
| Delete | `tm-api.sh delete-transaction <id>` |

**Create body** — `propertyId`, `type`, `amount`, `transactionDate` required:
```json
{"propertyId": 1, "type": "rent", "amount": 15000.0, "transactionDate": "2025-01-15"}
```

**Optional fields:** `tenantId`, `forMonth`, `comments`

**Update body** — partial, at least one field:
```json
{"amount": 16000.0, "comments": "Updated rent amount"}
```

**Transaction types:** `rent`, `security`, `payment_received`, `gas`, `electricity`, `water`, `maintenance`, `misc`

## Payment Logic

When summarizing balances or amounts owed:
- `payment_received` = funds collected from tenants (credit)
- All other types = outstanding amounts or expenses (debit)
- **Balance = sum of all non-payment_received amounts - sum of payment_received amounts**

## Behavior

1. **Confirm destructive operations** — before DELETE, confirm with the user unless they explicitly asked for deletion
2. **Show results clearly** — present responses as readable tables, not raw JSON
3. **The script validates inputs** — if it returns an error, fix the input and retry; do not bypass validation with raw curl
