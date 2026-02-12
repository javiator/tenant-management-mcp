# Production Deployment Configuration

This file contains the persistent configuration for deploying the TM MCP Server to Google Cloud Run. Use these settings for all production deployments.

## Core Configuration

- **GCP Project ID:** `gen-lang-client-0681882406`
- **Region:** `europe-west2` (London)
- **Service Name:** `tm-mcp-server`
- **Backend URL:** `https://tenant-backend-1084884913897.us-central1.run.app`

## Deployment Command

To deploy with these settings, run:

```bash
export GCP_PROJECT_ID=gen-lang-client-0681882406
printf "https://tenant-backend-1084884913897.us-central1.run.app
" | ./deploy.sh --region europe-west2
```

## Secrets Management

Ensure keys are synced before deployment if they have changed:

```bash
uv run python scripts/manage_keys.py sync-to-gcp
```
