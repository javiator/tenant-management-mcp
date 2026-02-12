# Production Authentication Strategy

## Overview

For the TM MCP Server deployed on Cloud Run, we recommend using **infrastructure-level authentication** rather than application-level middleware. This provides better security, performance, and maintainability.

## Recommended Approach: API Gateway with Authentication

### Option 1: Cloud Run with Identity-Aware Proxy (IAP) ⭐

**Best for:** Google Workspace organizations, internal tools

```
Client → Google IAP → Cloud Run → Backend API
         (OAuth 2.0)   (MCP Server)
```

**Setup:**
```bash
# 1. Deploy Cloud Run service
gcloud run deploy tm-mcp-server --image gcr.io/PROJECT/tm-mcp

# 2. Enable IAP
gcloud iap web enable \
  --resource-type=backend-services \
  --service=tm-mcp-server

# 3. Add authorized users
gcloud iap web add-iam-policy-binding \
  --resource-type=backend-services \
  --service=tm-mcp-server \
  --member=user:alice@example.com \
  --role=roles/iap.httpsResourceAccessor
```

**Pros:**
- ✅ Enterprise-grade OAuth 2.0
- ✅ No code changes needed
- ✅ Audit logs included
- ✅ Works with Google Workspace

**Cons:**
- ❌ Requires Google accounts
- ❌ Small additional cost

---

### Option 2: API Gateway with API Keys

**Best for:** External clients, programmatic access

```
Client → API Gateway → Cloud Run → Backend API
         (API Key)      (MCP Server)
```

**Setup:**
```bash
# 1. Create API Gateway config
# See: https://cloud.google.com/api-gateway/docs/quickstart

# 2. Deploy gateway
gcloud api-gateway gateways create mcp-gateway \
  --api=mcp-api \
  --api-config=mcp-config \
  --location=us-central1

# 3. Clients use gateway URL with API key
curl -H "Authorization: Bearer abc123" https://mcp-gateway-xxx.apigateway.dev/mcp/tools
```

**Pros:**
- ✅ Standard API key authentication
- ✅ Rate limiting included
- ✅ Works for any client

**Cons:**
- ❌ Additional component to manage
- ❌ Slight latency overhead

---

### Option 3: Reverse Proxy (Caddy/nginx) with Auth

**Best for:** Self-hosted, full control

```
Client → Caddy/nginx → Cloud Run → Backend API
         (Middleware)   (MCP Server)
```

**Example Caddyfile:**
```caddy
mcp.example.com {
    @unauthorized {
        not header Authorization "Bearer mcp_key1"
        not header Authorization "Bearer mcp_key2"
    }

    respond @unauthorized 401 {
        body "Unauthorized"
    }

    reverse_proxy https://tm-mcp-server-xxx.run.app
}
```

**Pros:**
- ✅ Full control
- ✅ Can add custom logic
- ✅ Works anywhere

**Cons:**
- ❌ Need to host proxy
- ❌ More infrastructure to manage

---

### Option 4: Application-Level (Current Approach)

**Status:** Simplified in this implementation

The MCP server validates `MCP_API_KEYS` at startup but doesn't enforce HTTP-level authentication due to FastMCP's design. Instead:

1. **For `stdio` transport:** Authentication handled by parent process
2. **For HTTP transports:** Use one of the infrastructure options above

**Why not application middleware?**
- FastMCP's ASGI app structure makes middleware injection complex
- Infrastructure-level auth is more secure and performant
- Separates concerns (app logic vs. security)

---

## Deployment Recommendations

### Development
```bash
# No authentication - fast iteration
unset MCP_API_KEYS
uv run tm-mcp --transport streamable-http
```

### Staging
```bash
# API Gateway or IAP
gcloud run deploy tm-mcp-server \
  --no-allow-unauthenticated  # Requires IAP/Gateway
```

### Production
```bash
# IAP + API Gateway (defense in depth)
# 1. IAP for user authentication
# 2. API Gateway for rate limiting
# 3. Backend token for MCP → Backend auth
```

---

## Migration Guide

If you've already set up `MCP_API_KEYS`:

### Quick Fix: Use Caddy as Sidecar

Deploy Caddy alongside Cloud Run:

```dockerfile
# Dockerfile.caddy
FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
```

```caddy
# Caddyfile
:8080 {
    @unauthorized {
        not header Authorization "Bearer {$MCP_API_KEYS}"
    }

    respond @unauthorized 401

    reverse_proxy localhost:8000
}
```

Then update Cloud Run to run both:
```bash
# Use a startup script that runs both Caddy and MCP server
```

---

## Security Comparison

| Method | Security | Performance | Cost | Complexity |
|--------|----------|-------------|------|------------|
| IAP | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | $ | ⭐⭐ |
| API Gateway | ⭐⭐⭐⭐ | ⭐⭐⭐ | $$ | ⭐⭐⭐ |
| Reverse Proxy | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | $ | ⭐⭐⭐⭐ |
| App-level | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | $ | ⭐⭐ |

---

## Recommendation

**For most use cases:** Use **Cloud Run + IAP**
- Simple setup
- Enterprise-grade security
- Low cost
- No code changes

**For external APIs:** Add **API Gateway** on top
- Standard API key management
- Rate limiting
- Works for non-Google users

---

## Implementation Status

✅ **Key Management System** - Working (manages keys for whatever auth you choose)
✅ **Server Validation** - Validates keys exist at startup
⚠️ **HTTP Middleware** - Deferred to infrastructure layer (recommended approach)

**Next Steps:**
1. Deploy to Cloud Run
2. Enable IAP or set up API Gateway
3. Test with real clients

---

## Questions?

See:
- [GCP_HOSTING_GUIDE.md](GCP_HOSTING_GUIDE.md) - Complete hosting guide
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment steps
- [KEY_MANAGEMENT.md](KEY_MANAGEMENT.md) - Managing API keys
