# Deployment Guide - Google Cloud Run

Complete guide for deploying the TM MCP Server to Google Cloud Platform.

## Overview

This guide covers:
1. **Prerequisites** - What you need before deploying
2. **Quick Deploy** - One-command deployment
3. **Manual Deployment** - Step-by-step process
4. **CI/CD Setup** - Automated deployments
5. **Post-Deployment** - Testing and monitoring
6. **Troubleshooting** - Common issues

---

## Prerequisites

### 1. Google Cloud Account

- Active GCP account with billing enabled
- Project created (or use existing)
- Required APIs enabled (script will enable automatically)

### 2. Local Tools

```bash
# Install gcloud CLI
# macOS
brew install --cask google-cloud-sdk

# Linux
curl https://sdk.cloud.google.com | bash

# Verify installation
gcloud --version
```

### 3. Authentication

```bash
# Login to GCP
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID
```

### 4. API Keys Prepared

```bash
# Generate keys for your users
uv run python scripts/manage_keys.py generate --name "Team Alpha"
uv run python scripts/manage_keys.py generate --name "Production Service"

# Verify keys
uv run python scripts/manage_keys.py list
```

---

## Quick Deploy (Recommended)

**One command to deploy everything:**

```bash
# Set your project ID
export GCP_PROJECT_ID=your-project-id

# Create and upload secrets
uv run python scripts/manage_keys.py sync-to-gcp

# Deploy!
./deploy.sh
```

The script will:
- ✅ Check prerequisites
- ✅ Enable required APIs
- ✅ Build Docker image
- ✅ Push to Container Registry
- ✅ Deploy to Cloud Run
- ✅ Configure secrets
- ✅ Show service URL

**That's it!** Your MCP server is now live.

---

## Manual Deployment (Step-by-Step)

### Step 1: Enable Required APIs

```bash
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  containerregistry.googleapis.com \
  secretmanager.googleapis.com
```

### Step 2: Create Secrets

```bash
# Option A: Use the key management script (recommended)
uv run python scripts/manage_keys.py sync-to-gcp

# Option B: Manual creation
echo "mcp_key1,mcp_key2" | gcloud secrets create mcp-api-keys --data-file=-
echo "your-backend-token" | gcloud secrets create backend-token --data-file=-
```

### Step 3: Grant Secret Access to Cloud Run

```bash
# Get the Cloud Run service account
PROJECT_NUMBER=$(gcloud projects describe $GCP_PROJECT_ID --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Grant access to secrets
gcloud secrets add-iam-policy-binding mcp-api-keys \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding backend-token \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"
```

### Step 4: Build and Push Docker Image

```bash
# Set variables
PROJECT_ID=your-project-id
IMAGE_NAME=tm-mcp

# Build and push
gcloud builds submit --tag gcr.io/$PROJECT_ID/$IMAGE_NAME
```

**Alternative: Local Docker build**
```bash
# Build locally
docker build -t gcr.io/$PROJECT_ID/$IMAGE_NAME .

# Push to GCR
docker push gcr.io/$PROJECT_ID/$IMAGE_NAME
```

### Step 5: Deploy to Cloud Run

```bash
gcloud run deploy tm-mcp-server \
  --image gcr.io/$PROJECT_ID/$IMAGE_NAME \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8000 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --min-instances 0 \
  --set-secrets MCP_API_KEYS=mcp-api-keys:latest,BACKEND_MCP_API_TOKEN=backend-token:latest \
  --set-env-vars BACKEND_MCP_BASE_URL=https://your-backend-api.com
```

### Step 6: Get Service URL

```bash
gcloud run services describe tm-mcp-server \
  --region us-central1 \
  --format 'value(status.url)'
```

---

## CI/CD Setup (Automated Deployments)

### GitHub Actions Setup

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches:
      - main

env:
  PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  SERVICE_NAME: tm-mcp-server
  REGION: us-central1

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v1

      - name: Build and Push Docker Image
        run: |
          gcloud builds submit \
            --tag gcr.io/$PROJECT_ID/tm-mcp

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy $SERVICE_NAME \
            --image gcr.io/$PROJECT_ID/tm-mcp \
            --region $REGION \
            --platform managed \
            --allow-unauthenticated \
            --set-secrets MCP_API_KEYS=mcp-api-keys:latest
```

**Required GitHub Secrets:**
- `GCP_PROJECT_ID` - Your GCP project ID
- `GCP_SA_KEY` - Service account JSON key

### Cloud Build Trigger

```bash
# Connect your repository
gcloud beta builds triggers create github \
  --repo-name=tenant-management-mcp \
  --repo-owner=YOUR_GITHUB_USERNAME \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml
```

---

## Post-Deployment

### Test the Deployment

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe tm-mcp-server \
  --region us-central1 \
  --format 'value(status.url)')

# Test health check (no auth required)
curl $SERVICE_URL/health

# Test with authentication
curl -H "Authorization: Bearer mcp_xxx" $SERVICE_URL/mcp/tools
```

### View Logs

```bash
# Stream logs
gcloud run services logs tail tm-mcp-server --region us-central1

# View recent logs
gcloud run services logs read tm-mcp-server \
  --region us-central1 \
  --limit 50
```

### Monitor Performance

```bash
# Open Cloud Run console
gcloud run services describe tm-mcp-server \
  --region us-central1 \
  --format 'value(status.url)' | \
  xargs -I {} open "https://console.cloud.google.com/run?project=$PROJECT_ID"
```

---

## Configuration Management

### Update Environment Variables

```bash
gcloud run services update tm-mcp-server \
  --region us-central1 \
  --set-env-vars BACKEND_MCP_BASE_URL=https://new-backend-url.com
```

### Update Secrets

```bash
# Update API keys
uv run python scripts/manage_keys.py generate --name "New User"
uv run python scripts/manage_keys.py sync-to-gcp

# Force Cloud Run to pick up new secret version
gcloud run services update tm-mcp-server \
  --region us-central1
```

### Update Resources

```bash
# Scale up memory/CPU
gcloud run services update tm-mcp-server \
  --region us-central1 \
  --memory 1Gi \
  --cpu 2
```

---

## Cost Optimization

### Pricing Estimates

**Free Tier (per month):**
- 2 million requests
- 360,000 GB-seconds
- 180,000 vCPU-seconds

**Beyond Free Tier:**
- ~$0.40 per million requests
- ~$0.00002 per GB-second
- ~$0.00001 per vCPU-second

**Estimated Monthly Cost:**
- Low traffic (< 1M requests/month): **FREE**
- Medium traffic (5M requests/month): **$2-5**
- High traffic (10M requests/month): **$5-15**

### Cost Reduction Tips

```bash
# Set min instances to 0 (scale to zero)
gcloud run services update tm-mcp-server \
  --region us-central1 \
  --min-instances 0

# Reduce max instances if you have low traffic
gcloud run services update tm-mcp-server \
  --region us-central1 \
  --max-instances 5

# Use smaller memory allocation
gcloud run services update tm-mcp-server \
  --region us-central1 \
  --memory 256Mi
```

---

## Security Hardening

### 1. Restrict Access with IAP (Optional)

If you want to add Google authentication on top of API keys:

```bash
# Enable Identity-Aware Proxy
gcloud alpha iap web enable \
  --resource-type=backend-services \
  --service=tm-mcp-server
```

### 2. Use VPC Connector

If your backend is in a private network:

```bash
# Create VPC connector
gcloud compute networks vpc-access connectors create mcp-connector \
  --region us-central1 \
  --network default \
  --range 10.8.0.0/28

# Update Cloud Run to use VPC
gcloud run services update tm-mcp-server \
  --region us-central1 \
  --vpc-connector mcp-connector
```

### 3. Enable Cloud Armor (DDoS Protection)

```bash
# Create security policy
gcloud compute security-policies create mcp-policy \
  --description "DDoS protection for MCP server"

# Apply rate limiting
gcloud compute security-policies rules create 1000 \
  --security-policy mcp-policy \
  --expression "true" \
  --action "rate-based-ban" \
  --rate-limit-threshold-count 100 \
  --rate-limit-threshold-interval-sec 60
```

---

## Troubleshooting

### Issue: "Permission denied" during deployment

**Solution:**
```bash
# Grant yourself necessary roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="user:your-email@example.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="user:your-email@example.com" \
  --role="roles/iam.serviceAccountUser"
```

### Issue: "Secret not found"

**Solution:**
```bash
# List secrets
gcloud secrets list

# Create missing secret
echo "value" | gcloud secrets create mcp-api-keys --data-file=-
```

### Issue: Service returns 500 errors

**Solution:**
```bash
# Check logs
gcloud run services logs read tm-mcp-server --region us-central1

# Common causes:
# 1. Missing BACKEND_MCP_BASE_URL
# 2. Invalid backend URL
# 3. Backend not reachable from Cloud Run
```

### Issue: "Cold start" latency

**Solution:**
```bash
# Set min-instances to keep container warm
gcloud run services update tm-mcp-server \
  --region us-central1 \
  --min-instances 1  # Costs ~$10/month
```

### Issue: Authentication not working

**Solution:**
```bash
# Check if secrets are mounted
gcloud run services describe tm-mcp-server \
  --region us-central1 \
  --format yaml | grep -A 5 secrets

# Verify secret value
gcloud secrets versions access latest --secret=mcp-api-keys
```

---

## Rollback

### Rollback to Previous Revision

```bash
# List revisions
gcloud run revisions list --service tm-mcp-server --region us-central1

# Rollback to specific revision
gcloud run services update-traffic tm-mcp-server \
  --region us-central1 \
  --to-revisions REVISION_NAME=100
```

---

## Multi-Region Deployment

Deploy to multiple regions for higher availability:

```bash
# Deploy to multiple regions
for REGION in us-central1 europe-west1 asia-east1; do
  gcloud run deploy tm-mcp-server \
    --image gcr.io/$PROJECT_ID/tm-mcp \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --set-secrets MCP_API_KEYS=mcp-api-keys:latest
done

# Set up global load balancer (requires additional setup)
```

---

## Next Steps

After deployment:

1. ✅ Test the service with API keys
2. ✅ Configure MCP clients (Claude Desktop, Cursor)
3. ✅ Set up monitoring alerts
4. ✅ Configure CI/CD for auto-deployment
5. ✅ Document the service URL for your team

---

## Quick Reference

```bash
# Deploy
./deploy.sh --project YOUR_PROJECT_ID

# Update
gcloud run services update tm-mcp-server --region us-central1

# Logs
gcloud run services logs tail tm-mcp-server --region us-central1

# Delete
gcloud run services delete tm-mcp-server --region us-central1
```
