# 🚀 Deploy to GCP - Quick Start

## Prerequisites (5 minutes)

```bash
# 1. Install gcloud CLI
brew install --cask google-cloud-sdk  # macOS
# or visit: https://cloud.google.com/sdk/install

# 2. Login and set project
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

## Deploy (3 commands)

```bash
# 1. Generate API keys
uv run python scripts/manage_keys.py generate --name "Your Team"

# 2. Upload keys to GCP
uv run python scripts/manage_keys.py sync-to-gcp

# 3. Deploy!
./deploy.sh
```

**That's it!** Your MCP server is live. ✅

## Get Your Service URL

```bash
gcloud run services describe tm-mcp-server \
  --region us-central1 \
  --format 'value(status.url)'
```

## Test It

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe tm-mcp-server --region us-central1 --format 'value(status.url)')

# Test health check
curl $SERVICE_URL/health

# Test with bearer token (replace with your token)
curl -H "Authorization: Bearer mcp_xxx" $SERVICE_URL/mcp/tools
```

## Configure MCP Client

**Claude Desktop** (`~/.config/claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "tenant-management": {
      "url": "YOUR_SERVICE_URL",
      "transport": {
        "type": "http",
        "headers": {
          "Authorization": "Bearer mcp_your_key_here"
        }
      }
    }
  }
}
```

## Common Commands

```bash
# View logs
gcloud run services logs tail tm-mcp-server --region us-central1

# Update service
gcloud run services update tm-mcp-server --region us-central1

# Delete service
gcloud run services delete tm-mcp-server --region us-central1
```

## Need Help?

- Full docs: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- Key management: [docs/KEY_MANAGEMENT.md](docs/KEY_MANAGEMENT.md)
- Authentication: [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md)

## Costs

- **FREE** for < 2M requests/month
- **$2-5** for ~5M requests/month
- Scale to zero when not in use

---

**Questions?** Check the [troubleshooting guide](docs/DEPLOYMENT.md#troubleshooting)
