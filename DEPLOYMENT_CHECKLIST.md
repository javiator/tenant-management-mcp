# Deployment Checklist - GCP Cloud Run

Step-by-step deployment guide with commands ready to copy-paste.

## Pre-Deployment Checklist

### ✅ Prerequisites

- [ ] GCP account with billing enabled
- [ ] Project created (or note existing project ID)
- [ ] `gcloud` CLI installed ([Install guide](https://cloud.google.com/sdk/install))
- [ ] Docker installed (for building images)
- [ ] API keys generated locally

---

## Step 1: Install gcloud CLI (if needed)

### macOS
```bash
brew install --cask google-cloud-sdk
```

### Linux
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

### Windows
Download from: https://cloud.google.com/sdk/install

**Verify installation:**
```bash
gcloud --version
```

---

## Step 2: Authenticate and Configure

```bash
# Login to GCP
gcloud auth login

# Set your project ID (replace with your actual project ID)
export GCP_PROJECT_ID=your-project-id
gcloud config set project $GCP_PROJECT_ID

# Verify
gcloud config list
```

---

## Step 3: Enable Required APIs

```bash
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  containerregistry.googleapis.com \
  secretmanager.googleapis.com
```

**Expected output:** `Operation "operations/..." finished successfully.`

---

## Step 4: Upload API Keys to Secret Manager

### Option A: Automated (Recommended)

```bash
# Sync all active keys from .keys.json to GCP
uv run python scripts/manage_keys.py sync-to-gcp
```

### Option B: Manual

```bash
# Export keys from key management
API_KEYS=$(uv run python scripts/manage_keys.py export)

# Create secret
echo "$API_KEYS" | gcloud secrets create mcp-api-keys --data-file=-

# Verify
gcloud secrets versions access latest --secret=mcp-api-keys
```

### Optional: Backend Token

```bash
# If you have a backend API token
echo "your-backend-token" | gcloud secrets create backend-token --data-file=-
```

---

## Step 5: Grant Secret Access to Cloud Run

```bash
# Get project number
PROJECT_NUMBER=$(gcloud projects describe $GCP_PROJECT_ID --format="value(projectNumber)")

# Cloud Run service account
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Grant access to mcp-api-keys
gcloud secrets add-iam-policy-binding mcp-api-keys \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"

# If you created backend-token, grant access to it too
# gcloud secrets add-iam-policy-binding backend-token \
#   --member="serviceAccount:${SERVICE_ACCOUNT}" \
#   --role="roles/secretmanager.secretAccessor"
```

---

## Step 6: Deploy with Automated Script

### Option A: Use deploy.sh (Easiest)

```bash
# Set project and region
export GCP_PROJECT_ID=your-project-id
export GCP_REGION=us-central1

# Deploy!
./deploy.sh
```

**The script will:**
1. Build Docker image
2. Push to Container Registry
3. Deploy to Cloud Run
4. Configure secrets
5. Show service URL

---

## Step 7: Manual Deployment (Alternative)

If you prefer manual control:

### 7.1: Build and Push Image

```bash
# Build image using Cloud Build (recommended)
gcloud builds submit --tag gcr.io/$GCP_PROJECT_ID/tm-mcp

# OR build locally and push
# docker build -t gcr.io/$GCP_PROJECT_ID/tm-mcp .
# docker push gcr.io/$GCP_PROJECT_ID/tm-mcp
```

### 7.2: Deploy to Cloud Run

```bash
# Get your backend URL
read -p "Enter your backend API URL: " BACKEND_URL

# Deploy
gcloud run deploy tm-mcp-server \
  --image gcr.io/$GCP_PROJECT_ID/tm-mcp \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8000 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --min-instances 0 \
  --set-secrets MCP_API_KEYS=mcp-api-keys:latest \
  --set-env-vars BACKEND_MCP_BASE_URL=$BACKEND_URL
```

**Optional: Add backend token**
```bash
# If you have backend token secret
--set-secrets MCP_API_KEYS=mcp-api-keys:latest,BACKEND_MCP_API_TOKEN=backend-token:latest
```

---

## Step 8: Get Service URL

```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe tm-mcp-server \
  --region us-central1 \
  --format 'value(status.url)')

echo "Service deployed at: $SERVICE_URL"
```

---

## Step 9: Test Deployment

### Test 1: Health Check (No Auth)

```bash
curl $SERVICE_URL/health
```

**Expected:** 404 (FastMCP doesn't have /health endpoint, but shows server responds)

### Test 2: With Bearer Token

```bash
# Get first bearer token
API_KEY=$(uv run python scripts/manage_keys.py export | cut -d',' -f1)

# Test MCP endpoint (will return 404 but shows auth is working)
curl -H "Authorization: Bearer $API_KEY" $SERVICE_URL/
```

### Test 3: View Logs

```bash
# Stream logs
gcloud run services logs tail tm-mcp-server --region us-central1

# Recent logs
gcloud run services logs read tm-mcp-server \
  --region us-central1 \
  --limit 50
```

---

## Step 10: Configure MCP Clients

### Claude Desktop

Edit `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tenant-management": {
      "url": "YOUR_SERVICE_URL",
      "transport": {
        "type": "http",
        "headers": {
          "Authorization": "Bearer YOUR_API_KEY"
        }
      }
    }
  }
}
```

Replace:
- `YOUR_SERVICE_URL` with your Cloud Run URL
- `YOUR_API_KEY` with one of your generated tokens

### Cursor

Edit `.cursor/mcp.json`:

```json
{
  "mcpServers": [
    {
      "name": "tenant-management",
      "url": "YOUR_SERVICE_URL",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  ]
}
```

---

## Troubleshooting

### Issue: "Permission denied"

```bash
# Grant yourself necessary roles
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="user:your-email@example.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="user:your-email@example.com" \
  --role="roles/iam.serviceAccountUser"
```

### Issue: "Secret not found"

```bash
# List secrets
gcloud secrets list

# Re-create if missing
uv run python scripts/manage_keys.py sync-to-gcp
```

### Issue: Service crashes on startup

```bash
# Check logs
gcloud run services logs read tm-mcp-server --region us-central1

# Common issues:
# 1. Missing BACKEND_MCP_BASE_URL
# 2. Backend not reachable from Cloud Run
# 3. Invalid secret configuration
```

### Issue: Authentication not working

```bash
# Verify secret value
gcloud secrets versions access latest --secret=mcp-api-keys

# Should show comma-separated keys like:
# mcp_xxx,mcp_yyy

# If empty or wrong, update:
uv run python scripts/manage_keys.py sync-to-gcp
gcloud run services update tm-mcp-server --region us-central1
```

---

## Post-Deployment Tasks

### Set up Monitoring

```bash
# View metrics in console
gcloud run services describe tm-mcp-server \
  --region us-central1 \
  --format 'value(status.url)' | \
  xargs -I {} open "https://console.cloud.google.com/run?project=$GCP_PROJECT_ID"
```

### Set up Alerts (Optional)

Create alerts for:
- High error rate (>5%)
- High latency (>1s p95)
- Low availability (<99%)

### Update Keys

```bash
# Generate new key
uv run python scripts/manage_keys.py generate --name "New User"

# Sync to GCP
uv run python scripts/manage_keys.py sync-to-gcp

# Cloud Run picks up new version automatically
# (may take a few minutes or restart service)
gcloud run services update tm-mcp-server --region us-central1
```

---

## Quick Command Reference

```bash
# Deploy
./deploy.sh

# View logs
gcloud run services logs tail tm-mcp-server --region us-central1

# Update service
gcloud run services update tm-mcp-server --region us-central1

# Scale
gcloud run services update tm-mcp-server \
  --region us-central1 \
  --min-instances 1 \
  --max-instances 20

# Delete
gcloud run services delete tm-mcp-server --region us-central1
```

---

## Estimated Time

- ✅ First-time setup: 15-20 minutes
- ✅ Subsequent deployments: 3-5 minutes (with script)

---

## Cost Estimate

**Free Tier:**
- 2 million requests/month
- 360,000 GB-seconds
- 180,000 vCPU-seconds

**Beyond Free Tier:**
- ~$0.40 per million requests
- ~$0.0000025 per GB-second
- ~$0.000024 per vCPU-second

**Typical monthly cost:** $0-10 for moderate usage

---

## Next Steps After Deployment

1. ✅ Test with MCP clients (Claude Desktop, Cursor)
2. ✅ Monitor logs and metrics
3. ✅ Set up alerting
4. ✅ Configure CI/CD (optional)
5. ✅ Add more users with key management scripts

---

## Support

- **Full deployment guide:** [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **GCP hosting guide:** [docs/GCP_HOSTING_GUIDE.md](docs/GCP_HOSTING_GUIDE.md)
- **Key management:** [docs/KEY_MANAGEMENT.md](docs/KEY_MANAGEMENT.md)
- **Authentication:** [docs/PRODUCTION_AUTH.md](docs/PRODUCTION_AUTH.md)

---

## Summary

Your deployment is complete when you see:

```
✅ Service URL: https://tm-mcp-server-xxx.run.app
✅ Authentication: Enabled
✅ Status: Healthy
✅ Logs: Clean
```

**Congratulations! Your MCP server is now live on GCP! 🎉**
