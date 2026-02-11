# Authentication Guide

Complete guide to API key authentication in the TM MCP Server.

## Overview

The TM MCP Server supports API key authentication to ensure only authorized clients can access your tenant management data.

### Security Model

```
┌─────────────┐
│   Client    │
│ (Claude AI) │
└──────┬──────┘
       │ X-API-Key: mcp_xxx
       ↓
┌─────────────────────┐
│  MCP Server         │
│  ┌───────────────┐  │
│  │ Auth Middleware│  │ ← Validates API key
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
1. **MCP Layer:** Client → MCP Server (API keys)
2. **Backend Layer:** MCP Server → Backend API (bearer token)

---

## Configuration

### Environment Variables

```bash
# .env file

# MCP Server Authentication (comma-separated API keys)
MCP_API_KEYS=mcp_key1,mcp_key2,mcp_key3

# Backend API Authentication (MCP → Backend)
BACKEND_MCP_API_TOKEN=your_backend_token
```

### Authentication States

| MCP_API_KEYS | Behavior |
|--------------|----------|
| Not set (empty) | ⚠️ **Authentication DISABLED** - All requests allowed (dev mode) |
| Set with keys | ✅ **Authentication ENABLED** - Only valid keys allowed |

---

## How Clients Authenticate

### HTTP Transport (Claude Desktop, Cursor, etc.)

Clients must include the API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: mcp_xqi4g228BUiXAJ5P9M5BBFQAmej9XtgY5Qol38zoG_Q" \
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
          "X-API-Key": "mcp_xqi4g228BUiXAJ5P9M5BBFQAmej9XtgY5Qol38zoG_Q"
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
        "X-API-Key": "mcp_xqi4g228BUiXAJ5P9M5BBFQAmej9XtgY5Qol38zoG_Q"
      }
    }
  ]
}
```

---

## Authentication Flow

### Successful Request

```
1. Client sends request with X-API-Key header
   ↓
2. MCP Server extracts key from header
   ↓
3. Server validates key against MCP_API_KEYS
   ✅ Key found in allowed list
   ↓
4. Request passes to MCP tools
   ↓
5. MCP tool calls backend with BACKEND_MCP_API_TOKEN
   ↓
6. Response returned to client
```

### Failed Authentication

```
1. Client sends request (missing or invalid key)
   ↓
2. MCP Server extracts key from header
   ↓
3. Server validates key against MCP_API_KEYS
   ❌ Key NOT found in allowed list
   ↓
4. Server returns 401 Unauthorized
   {
     "error": "Unauthorized",
     "message": "Invalid or missing API key. Provide X-API-Key header."
   }
```

---

## Testing Authentication

### Local Testing

```bash
# 1. Generate test keys
uv run python scripts/manage_keys.py generate --name "Test User"

# 2. Export keys to environment
export MCP_API_KEYS=$(uv run python scripts/manage_keys.py export)

# 3. Start server with authentication
uv run tm-mcp --transport streamable-http --host 127.0.0.1 --port 8000

# 4. Test without key (should fail)
curl http://127.0.0.1:8000/mcp/tools
# Expected: 401 Unauthorized

# 5. Test with valid key (should succeed)
curl -H "X-API-Key: mcp_xxx" http://127.0.0.1:8000/mcp/tools
# Expected: 200 OK
```

### Automated Testing

Run the test script:

```bash
./test_auth.sh
```

This tests:
- ❌ No API key → 401
- ❌ Invalid API key → 401
- ✅ Valid API key → 200
- ✅ Health check (no auth required) → 200

---

## Production Deployment

### Step 1: Generate Keys

```bash
# Generate keys for your users/teams
uv run python scripts/manage_keys.py generate --name "Team Alpha"
uv run python scripts/manage_keys.py generate --name "Team Beta"
uv run python scripts/manage_keys.py generate --name "Production Service"
```

### Step 2: Upload to GCP Secret Manager

```bash
# Sync all active keys to GCP
uv run python scripts/manage_keys.py sync-to-gcp
```

This creates/updates the `mcp-api-keys` secret with comma-separated keys.

### Step 3: Deploy Cloud Run with Secrets

```bash
gcloud run deploy tm-mcp-server \
  --image gcr.io/YOUR_PROJECT/tm-mcp:latest \
  --set-secrets MCP_API_KEYS=mcp-api-keys:latest,BACKEND_MCP_API_TOKEN=backend-token:latest
```

### Step 4: Verify Authentication

```bash
# Test without key (should fail)
curl https://your-mcp-server.run.app/mcp/tools
# Expected: 401

# Test with valid key (should succeed)
curl -H "X-API-Key: mcp_xxx" https://your-mcp-server.run.app/mcp/tools
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
- **Rotate keys regularly** - Every 90 days for users, 180 for services
- **Generate cryptographically secure keys** - Use the provided script
- **Store keys in Secret Manager** - Never in code or logs
- **Use separate keys per user/team** - Enables granular revocation
- **Monitor authentication failures** - Check Cloud Run logs
- **Revoke keys immediately on compromise** - Then sync to GCP

### ❌ DON'T

- **Don't commit keys to git** - `.keys.json` is git-ignored
- **Don't share keys in plain text** - Use 1Password/LastPass
- **Don't use the same key everywhere** - One key per user/team
- **Don't log API keys** - The middleware doesn't log keys
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
export MCP_API_KEYS="mcp_key1,mcp_key2"

# Or add to .env file
echo "MCP_API_KEYS=mcp_key1,mcp_key2" >> .env
```

---

### "401 Unauthorized" with Valid Key

**Problem:** Client gets 401 even with correct key

**Causes & Solutions:**

1. **Key not in MCP_API_KEYS**
   ```bash
   # Verify key is in the list
   echo $MCP_API_KEYS | grep "your_key"
   ```

2. **Typo in key**
   ```bash
   # Get the exact key from storage
   uv run python scripts/manage_keys.py show <key_id>
   ```

3. **Wrong header name**
   - Must be `X-API-Key` (case-insensitive)
   - NOT `Authorization`, `Api-Key`, etc.

4. **Key was revoked**
   ```bash
   # Check if key is still active
   uv run python scripts/manage_keys.py list
   ```

---

### "Server not using updated keys"

**Problem:** Updated keys in Secret Manager but server still uses old keys

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
- **API key usage** - Which keys are being used
- **Geographic distribution** - Where requests come from

---

## Key Rotation Process

### Scheduled Rotation (Every 90 days)

```bash
# 1. Generate new key for user
uv run python scripts/manage_keys.py generate --name "Alice Smith (2026-Q2)"

# 2. Share new key with user securely
# (via 1Password, encrypted email, etc.)

# 3. Sync to GCP
uv run python scripts/manage_keys.py sync-to-gcp

# 4. Wait for user to confirm they've updated their config

# 5. Revoke old key
uv run python scripts/manage_keys.py revoke <old_key_id>

# 6. Sync to GCP again
uv run python scripts/manage_keys.py sync-to-gcp
```

### Emergency Rotation (Compromise)

```bash
# 1. Immediately revoke compromised key
uv run python scripts/manage_keys.py revoke <compromised_key_id>

# 2. Sync to GCP (takes effect immediately)
uv run python scripts/manage_keys.py sync-to-gcp

# 3. Generate new key
uv run python scripts/manage_keys.py generate --name "Alice Smith (emergency)"

# 4. Share securely with user

# 5. Sync to GCP
uv run python scripts/manage_keys.py sync-to-gcp

# 6. Check logs for unauthorized usage of old key
gcloud logging read "jsonPayload.message=~'Unauthorized access attempt'"
```

---

## Implementation Details

### Code Structure

- **[src/tm_mcp/auth.py](../src/tm_mcp/auth.py)** - API key validation logic
- **[src/tm_mcp/server.py](../src/tm_mcp/server.py:46-67)** - Starlette middleware integration
- **[src/tm_mcp/config.py](../src/tm_mcp/config.py:30-34)** - MCP_API_KEYS configuration

### How Validation Works

```python
# 1. Keys loaded from environment on server start
MCP_API_KEYS = os.environ.get("MCP_API_KEYS", "")
allowed_keys = set(MCP_API_KEYS.split(","))

# 2. Each request extracts X-API-Key header
api_key = request.headers.get("X-API-Key")

# 3. Key checked against allowed set (O(1) lookup)
if api_key not in allowed_keys:
    return 401 Unauthorized
```

### Transport Compatibility

| Transport | Auth Support | Notes |
|-----------|--------------|-------|
| `streamable-http` | ✅ Full support | Starlette middleware |
| `sse` | ✅ Full support | Starlette middleware |
| `stdio` | ⚠️ Limited | No HTTP headers in stdio mode |

**Note:** For `stdio` transport, authentication is handled by the parent process spawning the MCP server.

---

## FAQ

### Q: Can I disable authentication for development?

A: Yes, just don't set `MCP_API_KEYS`:
```bash
# Development mode (no auth)
unset MCP_API_KEYS
uv run tm-mcp --transport streamable-http
```

### Q: How many keys can I have?

A: No hard limit, but Secret Manager has a 64KB limit per secret (~500-1000 keys).

### Q: Can I use the same key on multiple clients?

A: Yes, but not recommended. Use separate keys per user/team for better security and audit trails.

### Q: What if a user loses their key?

A: Use the show command to retrieve it:
```bash
uv run python scripts/manage_keys.py show <key_id>
```

### Q: Can I use bearer tokens instead of X-API-Key?

A: Yes, the middleware also accepts `Authorization: Bearer <token>` header.

---

## Next Steps

1. ✅ Generate keys for your users: [KEY_MANAGEMENT.md](KEY_MANAGEMENT.md)
2. ✅ Test authentication locally: `./test_auth.sh`
3. ✅ Deploy to Cloud Run with secrets
4. ✅ Configure MCP clients with keys
5. ✅ Set up monitoring and alerts
