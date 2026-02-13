# Authentication Guide

Complete guide to bearer token authentication in the TM MCP Server.

## Overview

The TM MCP Server supports bearer token authentication using the industry-standard `Authorization: Bearer <token>` header to ensure only authorized clients can access your tenant management data.

### Security Model

```
┌─────────────┐
│   Client    │
│ (Claude AI) │
└──────┬──────┘
       │ Authorization: Bearer mcp_xxx
       ↓
┌─────────────────────┐
│  MCP Server         │
│  ┌───────────────┐  │
│  │ Auth Middleware│  │ ← Validates bearer token
│  └───────┬───────┘  │
│          ↓          │
│  ┌───────────────┐  │
│  │  MCP Tools    │  │
│  └───────┬───────┘  │
│          ↓          │
└──────────┬──────────┘
           │ Authorization: Bearer backend_token
           ↓
┌─────────────────────┐
│  Backend API        │
│ (Spring Boot)       │
└─────────────────────┘
```

**Two layers of authentication:**
1. **MCP Layer:** Client → MCP Server (bearer tokens)
2. **Backend Layer:** MCP Server → Backend API (bearer token)

---

## Configuration

### Environment Variables

```bash
# .env file

# MCP Server Authentication (comma-separated bearer tokens)
MCP_API_KEYS=mcp_token1,mcp_token2,mcp_token3

# Backend API Authentication (MCP → Backend)
BACKEND_MCP_API_TOKEN=your_backend_token
```

### Authentication States

| MCP_API_KEYS | Behavior |
|--------------|----------|
| Not set (empty) | ⚠️ **Authentication DISABLED** - All requests allowed (dev mode) |
| Set with tokens | ✅ **Authentication ENABLED** - Only valid tokens allowed |

---

## How Clients Authenticate

### HTTP Transport (Claude Desktop, Cursor, etc.)

Clients must include the token in the `Authorization` header using the Bearer scheme:

```bash
curl -H "Authorization: Bearer mcp_xqi4g228BUiXAJ5P9M5BBFQAmej9XtgY5Qol38zoG_Q" \
     -H "Content-Type: application/json" \
     https://your-mcp-server.run.app/mcp/tools
```

### MCP Client Configuration

**Claude Desktop** (`~/.config/claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "tenant-management": {
      "url": "https://your-mcp-server.run.app",
      "transport": {
        "type": "http",
        "headers": {
          "Authorization": "Bearer mcp_xqi4g228BUiXAJ5P9M5BBFQAmej9XtgY5Qol38zoG_Q"
        }
      }
    }
  }
}
```

**Cursor** (`.cursor/mcp.json`):
```json
{
  "mcpServers": [
    {
      "name": "tenant-management",
      "url": "https://your-mcp-server.run.app",
      "headers": {
        "Authorization": "Bearer mcp_xqi4g228BUiXAJ5P9M5BBFQAmej9XtgY5Qol38zoG_Q"
      }
    }
  ]
}
```

---

## Authentication Flow

### Successful Request

```
1. Client sends request with Authorization: Bearer <token> header
   ↓
2. MCP Server extracts token from Authorization header
   ↓
3. Server validates token against MCP_API_KEYS
   ✅ Token found in allowed list
   ↓
4. Request passes to MCP tools
   ↓
5. MCP tool calls backend with BACKEND_MCP_API_TOKEN
   ↓
6. Response returned to client
```

### Failed Authentication

```
1. Client sends request (missing or invalid token)
   ↓
2. MCP Server checks Authorization header
   ↓
3. Server validates token against MCP_API_KEYS
   ❌ Token NOT found in allowed list
   ↓
4. Server returns 401 Unauthorized
   {
     "error": "Unauthorized",
     "message": "Missing or invalid bearer token. Provide Authorization: Bearer <token> header."
   }
```

---

## Testing Authentication

### Local Testing

```bash
# 1. Generate test tokens
uv run python scripts/manage_keys.py generate --name "Test User"

# 2. Export tokens to environment
export MCP_API_KEYS=$(uv run python scripts/manage_keys.py export)

# 3. Start server with authentication
uv run tm-mcp --transport streamable-http --host 127.0.0.1 --port 8000

# 4. Test without token (should fail)
curl http://127.0.0.1:8000/mcp/tools
# Expected: 401 Unauthorized

# 5. Test with valid token (should succeed)
curl -H "Authorization: Bearer mcp_xxx" http://127.0.0.1:8000/mcp/tools
# Expected: 200 OK
```

### Automated Testing

Run the test script:

```bash
./test_auth.sh
```

This tests:
- ❌ No bearer token → 401
- ❌ Invalid bearer token → 401
- ✅ Valid bearer token → 200
- ✅ Health check (no auth required) → 200

---

## Production Deployment

### Step 1: Generate Tokens

```bash
# Generate tokens for your users/teams
uv run python scripts/manage_keys.py generate --name "Team Alpha"
uv run python scripts/manage_keys.py generate --name "Team Beta"
uv run python scripts/manage_keys.py generate --name "Production Service"
```

### Step 2: Upload to GCP Secret Manager

```bash
# Sync all active tokens to GCP
uv run python scripts/manage_keys.py sync-to-gcp
```

This creates/updates the `mcp-api-keys` secret with comma-separated tokens.

### Step 3: Deploy Cloud Run with Secrets

```bash
gcloud run deploy tm-mcp-server \
  --image gcr.io/YOUR_PROJECT/tm-mcp:latest \
  --set-secrets MCP_API_KEYS=mcp-api-keys:latest,BACKEND_MCP_API_TOKEN=backend-token:latest
```

### Step 4: Verify Authentication

```bash
# Test without token (should fail)
curl https://your-mcp-server.run.app/mcp/tools
# Expected: 401

# Test with valid token (should succeed)
curl -H "Authorization: Bearer mcp_xxx" https://your-mcp-server.run.app/mcp/tools
# Expected: 200
```

---

## Middleware Behavior

### Protected Endpoints

All MCP endpoints require authentication:
- `/mcp/*` - All MCP protocol endpoints
- Custom tool endpoints

### Unprotected Endpoints

These endpoints work WITHOUT authentication:
- `/health` - Health check
- `/healthz` - Alternative health check
- `/` - Root endpoint

This allows load balancers and monitoring systems to check server health.

---

## Security Best Practices

### ✅ DO

- **Use HTTPS in production** - Cloud Run provides this automatically
- **Rotate tokens regularly** - Every 90 days for users, 180 for services
- **Generate cryptographically secure tokens** - Use the provided script
- **Store tokens in Secret Manager** - Never in code or logs
- **Use separate tokens per user/team** - Enables granular revocation
- **Monitor authentication failures** - Check Cloud Run logs
- **Revoke tokens immediately on compromise** - Then sync to GCP

### ❌ DON'T

- **Don't commit tokens to git** - `.keys.json` is git-ignored
- **Don't share tokens in plain text** - Use 1Password/LastPass
- **Don't use the same token everywhere** - One token per user/team
- **Don't log bearer tokens** - The middleware doesn't log tokens
- **Don't disable auth in production** - Only for local development

---

## Troubleshooting

### "Authentication DISABLED" Warning

**Problem:** Server logs show "Authentication DISABLED"

**Cause:** `MCP_API_KEYS` environment variable is empty or not set

**Solution:**
```bash
# Check if variable is set
echo $MCP_API_KEYS

# Set it
export MCP_API_KEYS="mcp_token1,mcp_token2"

# Or add to .env file
echo "MCP_API_KEYS=mcp_token1,mcp_token2" >> .env
```

---

### "401 Unauthorized" with Valid Token

**Problem:** Client gets 401 even with correct token

**Causes & Solutions:**

1. **Token not in MCP_API_KEYS**
   ```bash
   # Verify token is in the list
   echo $MCP_API_KEYS | grep "your_token"
   ```

2. **Typo in token**
   ```bash
   # Get the exact token from storage
   uv run python scripts/manage_keys.py show <key_id>
   ```

3. **Wrong header format**
   - Must be `Authorization: Bearer <token>`
   - NOT `X-API-Key`, `Api-Key`, or bare `Authorization` without Bearer prefix

4. **Token was revoked**
   ```bash
   # Check if token is still active
   uv run python scripts/manage_keys.py list
   ```

---

### "Server not using updated tokens"

**Problem:** Updated tokens in Secret Manager but server still uses old tokens

**Solution:** Cloud Run needs to be redeployed or restarted to pick up new secret versions

```bash
# Force new deployment
gcloud run services update tm-mcp-server \
  --region us-central1

# Or trigger a new revision
gcloud run deploy tm-mcp-server \
  --image gcr.io/YOUR_PROJECT/tm-mcp:latest
```

---

## Monitoring & Logging

### Cloud Run Logs

View authentication failures:

```bash
gcloud logging read "resource.type=cloud_run_revision AND \
  jsonPayload.message=~'Unauthorized access attempt'" \
  --limit 50
```

### Metrics to Track

- **401 error rate** - High rate = possible attack or misconfigured clients
- **Token usage** - Which tokens are being used
- **Geographic distribution** - Where requests come from

---

## Token Rotation Process

### Scheduled Rotation (Every 90 days)

```bash
# 1. Generate new token for user
uv run python scripts/manage_keys.py generate --name "Alice Smith (2026-Q2)"

# 2. Share new token with user securely
# (via 1Password, encrypted email, etc.)

# 3. Sync to GCP
uv run python scripts/manage_keys.py sync-to-gcp

# 4. Wait for user to confirm they've updated their config

# 5. Revoke old token
uv run python scripts/manage_keys.py revoke <old_key_id>

# 6. Sync to GCP again
uv run python scripts/manage_keys.py sync-to-gcp
```

### Emergency Rotation (Compromise)

```bash
# 1. Immediately revoke compromised token
uv run python scripts/manage_keys.py revoke <compromised_key_id>

# 2. Sync to GCP (takes effect immediately)
uv run python scripts/manage_keys.py sync-to-gcp

# 3. Generate new token
uv run python scripts/manage_keys.py generate --name "Alice Smith (emergency)"

# 4. Share securely with user

# 5. Sync to GCP
uv run python scripts/manage_keys.py sync-to-gcp

# 6. Check logs for unauthorized usage of old token
gcloud logging read "jsonPayload.message=~'Unauthorized access attempt'"
```

---

## Implementation Details

### Code Structure

- **[src/tm_mcp/auth.py](../src/tm_mcp/auth.py)** - Bearer token validation logic
- **[src/tm_mcp/server.py](../src/tm_mcp/server.py)** - Starlette middleware integration
- **[src/tm_mcp/config.py](../src/tm_mcp/config.py)** - MCP_API_KEYS configuration

### How Validation Works

```python
# 1. Tokens loaded from environment on server start
MCP_API_KEYS = os.environ.get("MCP_API_KEYS", "")
allowed_tokens = set(MCP_API_KEYS.split(","))

# 2. Each request extracts Authorization header
auth_header = request.headers.get("Authorization")
token = auth_header.removeprefix("Bearer ")

# 3. Token checked against allowed set (O(1) lookup)
if token not in allowed_tokens:
    return 401 Unauthorized
```

### Transport Compatibility

| Transport | Auth Support | Notes |
|-----------|--------------|-------|
| `streamable-http` | ✅ Full support | Recommended. Starlette middleware |
| `sse` | ✅ Full support | Deprecated — use `streamable-http` instead |
| `stdio` | ⚠️ Limited | No HTTP headers in stdio mode |

**Note:** For `stdio` transport, authentication is handled by the parent process spawning the MCP server. The `sse` transport is deprecated in the MCP spec — use `streamable-http` for all new deployments.

---

## FAQ

### Q: Can I disable authentication for development?

A: Yes, just don't set `MCP_API_KEYS`:
```bash
# Development mode (no auth)
unset MCP_API_KEYS
uv run tm-mcp --transport streamable-http
```

### Q: How many tokens can I have?

A: No hard limit, but Secret Manager has a 64KB limit per secret (~500-1000 tokens).

### Q: Can I use the same token on multiple clients?

A: Yes, but not recommended. Use separate tokens per user/team for better security and audit trails.

### Q: What if a user loses their token?

A: Use the show command to retrieve it:
```bash
uv run python scripts/manage_keys.py show <key_id>
```

### Q: Why Authorization: Bearer instead of X-API-Key?

A: `Authorization: Bearer` is the industry-standard authentication header defined in [RFC 6750](https://datatracker.ietf.org/doc/html/rfc6750). It is widely supported by HTTP clients, proxies, API gateways, and security tooling out of the box.

---

## Next Steps

1. ✅ Generate tokens for your users: [KEY_MANAGEMENT.md](KEY_MANAGEMENT.md)
2. ✅ Test authentication locally: `./test_auth.sh`
3. ✅ Deploy to Cloud Run with secrets
4. ✅ Configure MCP clients with bearer tokens
5. ✅ Set up monitoring and alerts
