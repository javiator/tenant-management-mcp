# Complete GCP Hosting Guide

End-to-end guide for hosting the TM MCP Server on Google Cloud Platform with authentication.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Deployment Options](#deployment-options)
5. [Quick Deployment](#quick-deployment)
6. [Configuration](#configuration)
7. [Monitoring & Maintenance](#monitoring--maintenance)
8. [Cost Analysis](#cost-analysis)
9. [Security Considerations](#security-considerations)
10. [Troubleshooting](#troubleshooting)

---

## Overview

### What You're Building

```
┌──────────────────┐
│   AI Clients     │
│ Claude, Cursor   │
└────────┬─────────┘
         │ HTTPS + Authorization: Bearer
         ↓
┌──────────────────────────────────┐
│   Google Cloud Platform          │
│                                  │
│  ┌────────────────────────────┐ │
│  │  Cloud Load Balancer       │ │
│  │  (HTTPS/TLS termination)   │ │
│  └─────────────┬──────────────┘ │
│                ↓                 │
│  ┌────────────────────────────┐ │
│  │  Cloud Run Service         │ │
│  │  - TM MCP Server           │ │
│  │  - Bearer token auth        │ │
│  │  - Auto-scaling            │ │
│  └─────────────┬──────────────┘ │
│                ↓                 │
│  ┌────────────────────────────┐ │
│  │  Secret Manager            │ │
│  │  - API keys                │ │
│  │  - Backend token           │ │
│  └────────────────────────────┘ │
└──────────────────────────────────┘
         │ HTTPS + Bearer token
         ↓
┌──────────────────┐
│  Backend API     │
│  (Spring Boot)   │
└──────────────────┘
```

### Key Features

✅ **Serverless** - No infrastructure management
✅ **Auto-scaling** - Scales from 0 to N instances
✅ **Secure** - HTTPS, API keys, Secret Manager
✅ **Cost-effective** - Pay per use, free tier available
✅ **Global** - Deploy to multiple regions
✅ **Reliable** - 99.95% SLA from Google

---

## Architecture

### Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| **MCP Server** | Expose tenant management APIs | Python + FastMCP |
| **Cloud Run** | Serverless container hosting | Google Cloud Run |
| **Secret Manager** | Store API keys securely | GCP Secret Manager |
| **Container Registry** | Store Docker images | Google Container Registry |
| **Cloud Build** | Build and deploy images | GCP Cloud Build |
| **Load Balancer** | HTTPS termination, routing | Built into Cloud Run |

### Authentication Flow

```
1. Client → Request with Authorization: Bearer <token> header
2. Cloud Run → Reads MCP_API_KEYS from Secret Manager
3. Middleware → Validates bearer token
4. If valid → Pass to MCP tools
5. MCP Server → Calls backend with BACKEND_MCP_API_TOKEN
6. Backend → Returns data
7. Cloud Run → Returns to client
```

---

## Prerequisites

### 1. GCP Account Setup

- [ ] GCP account with billing enabled
- [ ] Project created (or use existing)
- [ ] Billing account linked to project

**Create a project:**
```bash
gcloud projects create YOUR_PROJECT_ID --name="TM MCP Server"
gcloud config set project YOUR_PROJECT_ID

# Link billing (find billing account ID first)
gcloud billing accounts list
gcloud billing projects link YOUR_PROJECT_ID \
  --billing-account=BILLING_ACCOUNT_ID
```

### 2. Local Tools

- [ ] `gcloud` CLI installed
- [ ] `docker` installed (optional, for local testing)
- [ ] `uv` installed (for key management)

### 3. API Keys Generated

- [ ] At least one API key generated
- [ ] Keys stored in `.keys.json`

```bash
uv run python scripts/manage_keys.py generate --name "Production"
```

---

## Deployment Options

### Option 1: Quick Deploy (Recommended) ⭐

**Best for:** Getting started, small teams

**Time:** 5-10 minutes

```bash
./deploy.sh
```

**What it does:**
- ✅ Checks prerequisites
- ✅ Enables APIs
- ✅ Builds Docker image
- ✅ Deploys to Cloud Run
- ✅ Configures secrets

---

### Option 2: Manual Deployment

**Best for:** Understanding the process, custom configuration

**Time:** 15-20 minutes

See [DEPLOYMENT.md](DEPLOYMENT.md) for step-by-step guide.

---

### Option 3: CI/CD Pipeline

**Best for:** Production, automated deployments

**Time:** 30 minutes initial setup

See [CI/CD Setup](#cicd-setup) below.

---

## Quick Deployment

### Step 1: Prepare

```bash
# Set your project
export GCP_PROJECT_ID=your-project-id

# Generate API keys
uv run python scripts/manage_keys.py generate --name "Team Alpha"
uv run python scripts/manage_keys.py generate --name "Production Service"
```

### Step 2: Upload Secrets

```bash
# Upload API keys to GCP
uv run python scripts/manage_keys.py sync-to-gcp

# (Optional) Upload backend token
echo "your-backend-token" | \
  gcloud secrets create backend-token --data-file=-
```

### Step 3: Deploy

```bash
# One command deployment
./deploy.sh
```

### Step 4: Get Service URL

```bash
gcloud run services describe tm-mcp-server \
  --region us-central1 \
  --format 'value(status.url)'
```

### Step 5: Test

```bash
SERVICE_URL=$(gcloud run services describe tm-mcp-server \
  --region us-central1 --format 'value(status.url)')

# Health check
curl $SERVICE_URL/health

# With bearer token
API_KEY=$(uv run python scripts/manage_keys.py export | cut -d',' -f1)
curl -H "Authorization: Bearer $API_KEY" $SERVICE_URL/mcp/tools
```

---

## Configuration

### Environment Variables

Set in Cloud Run:

```bash
gcloud run services update tm-mcp-server \
  --region us-central1 \
  --set-env-vars KEY=VALUE
```

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `BACKEND_MCP_BASE_URL` | Backend API URL | ✅ Yes | `https://api.example.com` |
| `MCP_API_KEYS` | API keys (from Secret) | ✅ Yes | (from Secret Manager) |
| `BACKEND_MCP_API_TOKEN` | Backend auth token (from Secret) | Optional | (from Secret Manager) |

### Secrets

Secrets are injected as environment variables:

```bash
# Update secrets mapping
gcloud run services update tm-mcp-server \
  --region us-central1 \
  --set-secrets MCP_API_KEYS=mcp-api-keys:latest
```

### Resources

```bash
# Update memory/CPU
gcloud run services update tm-mcp-server \
  --region us-central1 \
  --memory 512Mi \
  --cpu 1
```

### Scaling

```bash
# Configure auto-scaling
gcloud run services update tm-mcp-server \
  --region us-central1 \
  --min-instances 0 \
  --max-instances 10
```

---

## Monitoring & Maintenance

### View Logs

```bash
# Stream logs
gcloud run services logs tail tm-mcp-server --region us-central1

# Recent logs
gcloud run services logs read tm-mcp-server \
  --region us-central1 \
  --limit 100
```

### Monitor Metrics

```bash
# Open Cloud Console metrics
gcloud run services describe tm-mcp-server \
  --region us-central1 \
  --format 'value(status.url)'
```

**Key metrics to watch:**
- Request count
- Request latency (p50, p95, p99)
- Error rate (5xx errors)
- Container instance count
- Memory utilization
- CPU utilization

### Set Up Alerts

```bash
# Example: Alert on high error rate
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="TM MCP High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=0.05 \
  --condition-metric-filter='resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_count"'
```

### Update API Keys

```bash
# Add new key
uv run python scripts/manage_keys.py generate --name "New User"

# Upload to GCP
uv run python scripts/manage_keys.py sync-to-gcp

# Force Cloud Run to reload (picks up new secret version)
gcloud run services update tm-mcp-server --region us-central1
```

### Update Backend URL

```bash
gcloud run services update tm-mcp-server \
  --region us-central1 \
  --set-env-vars BACKEND_MCP_BASE_URL=https://new-backend.com
```

---

## Cost Analysis

### Pricing Components

**Cloud Run:**
- Requests: $0.40 per million
- Memory: $0.00000250 per GB-second
- CPU: $0.00002400 per vCPU-second
- Free tier: 2M requests, 360k GB-sec, 180k vCPU-sec/month

**Secret Manager:**
- $0.06 per 10k access operations
- First 6 versions of each secret free

**Container Registry:**
- Storage: $0.026 per GB/month
- Network egress: Varies by region

### Cost Estimates

**Scenario 1: Low Traffic (Free Tier)**
- 1M requests/month
- Avg 200ms response time
- 512Mi memory, 1 vCPU
- **Cost: $0/month** (within free tier)

**Scenario 2: Medium Traffic**
- 5M requests/month
- Avg 200ms response time
- 512Mi memory, 1 vCPU
- **Cost: ~$3-5/month**

**Scenario 3: High Traffic**
- 20M requests/month
- Avg 200ms response time
- 512Mi memory, 1 vCPU
- **Cost: ~$10-15/month**

### Cost Optimization

```bash
# Scale to zero when idle
gcloud run services update tm-mcp-server \
  --region us-central1 \
  --min-instances 0

# Reduce memory
gcloud run services update tm-mcp-server \
  --region us-central1 \
  --memory 256Mi

# Set request timeout
gcloud run services update tm-mcp-server \
  --region us-central1 \
  --timeout 30s
```

---

## Security Considerations

### 1. API Key Security

✅ **DO:**
- Generate keys with cryptographic randomness
- Use separate keys per user/team
- Rotate keys every 90 days
- Store keys in Secret Manager
- Revoke compromised keys immediately

❌ **DON'T:**
- Commit keys to git
- Share keys in plain text
- Use the same key for everyone
- Log API keys

### 2. Network Security

```bash
# Restrict access to specific IP ranges (if needed)
gcloud run services update tm-mcp-server \
  --region us-central1 \
  --ingress internal-and-cloud-load-balancing

# Use VPC connector for private backend
gcloud run services update tm-mcp-server \
  --region us-central1 \
  --vpc-connector your-connector
```

### 3. Container Security

- ✅ Non-root user in Docker image
- ✅ Minimal base image (python:3.11-slim)
- ✅ No secrets in image layers
- ✅ Regular dependency updates

### 4. Audit Logging

```bash
# Enable data access logs
gcloud projects set-iam-policy $PROJECT_ID policy.yaml
```

---

## Troubleshooting

### Common Issues

#### Issue: "Permission denied"

**Solution:**
```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="user:your-email@example.com" \
  --role="roles/run.admin"
```

#### Issue: Service returns 500

**Check logs:**
```bash
gcloud run services logs read tm-mcp-server --region us-central1
```

**Common causes:**
- Missing `BACKEND_MCP_BASE_URL`
- Invalid backend URL
- Backend not reachable

#### Issue: Authentication not working

**Verify secrets:**
```bash
gcloud secrets versions access latest --secret=mcp-api-keys
```

**Check service configuration:**
```bash
gcloud run services describe tm-mcp-server \
  --region us-central1 \
  --format yaml
```

#### Issue: Cold start latency

**Solution: Keep warm**
```bash
gcloud run services update tm-mcp-server \
  --region us-central1 \
  --min-instances 1  # Costs extra, but eliminates cold starts
```

---

## CI/CD Setup

### GitHub Actions

Create `.github/workflows/deploy-to-gcp.yml`:

```yaml
name: Deploy to GCP

on:
  push:
    branches: [main]

env:
  PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  REGION: us-central1

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - uses: google-github-actions/setup-gcloud@v1

      - run: |
          gcloud builds submit --tag gcr.io/$PROJECT_ID/tm-mcp
          gcloud run deploy tm-mcp-server \
            --image gcr.io/$PROJECT_ID/tm-mcp \
            --region $REGION
```

**Required secrets:**
- `GCP_PROJECT_ID`
- `GCP_SA_KEY` (service account JSON key)

### Cloud Build Trigger

```bash
gcloud beta builds triggers create github \
  --repo-name=tenant-management-mcp \
  --repo-owner=YOUR_GITHUB_USERNAME \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml
```

---

## Next Steps

After deployment:

1. ✅ [Configure MCP clients](AUTHENTICATION.md#how-clients-authenticate)
2. ✅ [Set up monitoring alerts](#set-up-alerts)
3. ✅ [Configure CI/CD](#cicd-setup)
4. ✅ [Test with real clients](../README.md#mcp-client-integration)
5. ✅ [Plan key rotation schedule](KEY_MANAGEMENT.md#key-rotation-process)

---

## Quick Reference

```bash
# Deploy
./deploy.sh

# View logs
gcloud run services logs tail tm-mcp-server --region us-central1

# Update service
gcloud run services update tm-mcp-server --region us-central1

# Scale
gcloud run services update tm-mcp-server --min-instances 1 --region us-central1

# Delete
gcloud run services delete tm-mcp-server --region us-central1
```

---

## Support

- **Deployment Issues:** [DEPLOYMENT.md](DEPLOYMENT.md#troubleshooting)
- **Authentication:** [AUTHENTICATION.md](AUTHENTICATION.md)
- **Key Management:** [KEY_MANAGEMENT.md](KEY_MANAGEMENT.md)
- **Quick Start:** [DEPLOY_QUICKSTART.md](../DEPLOY_QUICKSTART.md)
