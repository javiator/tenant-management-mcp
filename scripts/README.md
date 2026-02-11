# API Key Management Scripts

This directory contains utilities for managing API keys for the TM MCP Server.

## Quick Start

### 1. Generate a new key for a user/team

```bash
python scripts/manage_keys.py generate --name "Team Alpha"
```

Output:
```
✅ New API key generated:
   ID:   a1b2c3d4
   Name: Team Alpha
   Key:  mcp_vXY7Kp9Lm3Qr8Wz4Nt6Jh2Fg5Cd1As0

⚠️  Save this key securely - it won't be shown again!
```

### 2. List all active keys

```bash
python scripts/manage_keys.py list
```

Output:
```
ID           Name                      Created              Status
----------------------------------------------------------------------
a1b2c3d4     Team Alpha                2026-02-11           Active
e5f6g7h8     John Doe                  2026-02-10           Active
```

### 3. Show full key details (when user loses key)

```bash
python scripts/manage_keys.py show a1b2
```

### 4. Sync keys to GCP Secret Manager

```bash
python scripts/manage_keys.py sync-to-gcp
```

This uploads all active keys to GCP Secret Manager as a comma-separated list.

### 5. Revoke a key

```bash
python scripts/manage_keys.py revoke a1b2c3d4
```

Then sync to GCP:
```bash
python scripts/manage_keys.py sync-to-gcp
```

## Key Storage

Keys are stored locally in `.keys.json` (git-ignored) with this structure:

```json
{
  "keys": [
    {
      "id": "a1b2c3d4",
      "key": "mcp_vXY7Kp9Lm3Qr8Wz4Nt6Jh2Fg5Cd1As0",
      "name": "Team Alpha",
      "created": "2026-02-11T10:30:00",
      "last_used": null
    }
  ],
  "revoked": []
}
```

## Security Best Practices

1. **Never commit `.keys.json`** - It's git-ignored by default
2. **Backup `.keys.json`** securely (e.g., encrypted 1Password vault)
3. **Share keys securely** - Use 1Password, LastPass, or encrypted email
4. **Rotate keys periodically** - Generate new key, share with user, revoke old key
5. **Use descriptive names** - Makes auditing easier

## Deployment Workflow

```bash
# 1. Generate keys for your users
python scripts/manage_keys.py generate --name "Team Alpha"
python scripts/manage_keys.py generate --name "John Doe"
python scripts/manage_keys.py generate --name "Production Service"

# 2. Sync to GCP
python scripts/manage_keys.py sync-to-gcp

# 3. Deploy or update Cloud Run service
gcloud run services update tm-mcp-server \
  --set-secrets MCP_API_KEYS=mcp-api-keys:latest
```

## Advanced Usage

### Export keys for manual upload

```bash
# Get comma-separated key list
python scripts/manage_keys.py export

# Pipe to file
python scripts/manage_keys.py export > keys.txt

# Upload manually
cat keys.txt | gcloud secrets versions add mcp-api-keys --data-file=-
```

### Audit trail

All revoked keys are kept in `.keys.json` under the `revoked` array for audit purposes.

## Troubleshooting

### "gcloud CLI not found"

Install the Google Cloud SDK:
```bash
# macOS
brew install --cask google-cloud-sdk

# Linux
curl https://sdk.cloud.google.com | bash

# Windows
# Download from: https://cloud.google.com/sdk/install
```

### "Permission denied" when syncing to GCP

Authenticate with gcloud:
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

Ensure you have permissions:
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member=user:your-email@example.com \
  --role=roles/secretmanager.admin
```
