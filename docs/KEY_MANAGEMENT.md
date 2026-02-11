# API Key Management Guide

Complete guide for creating and managing API keys for the TM MCP Server.

## Overview

You have **three options** for managing API keys:

1. **Manual CLI Tool** (Recommended for small teams) ⭐
2. **Admin API Endpoints** (For larger teams)
3. **Database-backed Management** (Enterprise-grade)

---

## Option 1: Manual CLI Tool ⭐ (Implemented)

**Best for:** Small teams (1-20 users), simple deployments

### Setup

The CLI tool stores keys in `.keys.json` (git-ignored) and syncs to GCP Secret Manager.

```bash
# No setup needed - just run the script!
python scripts/manage_keys.py --help
```

### Daily Usage

#### Create a key for a new user

```bash
# Generate key
python scripts/manage_keys.py generate --name "Alice Smith"

# Output shows the key - share it securely with Alice
# Then sync to GCP
python scripts/manage_keys.py sync-to-gcp
```

#### List all keys

```bash
python scripts/manage_keys.py list
```

#### Revoke a key

```bash
# Find the key ID from list command
python scripts/manage_keys.py list

# Revoke it
python scripts/manage_keys.py revoke a1b2c3d4

# Sync to GCP
python scripts/manage_keys.py sync-to-gcp
```

#### User lost their key?

```bash
# Show the full key again
python scripts/manage_keys.py show a1b2c3d4
```

### Backup Strategy

```bash
# Backup .keys.json to encrypted storage
# Option 1: Encrypt with GPG
gpg -c .keys.json  # Creates .keys.json.gpg

# Option 2: Store in 1Password/LastPass as secure note
# Copy contents and save as secure note

# Option 3: Backup to GCS bucket
gsutil cp .keys.json gs://your-backup-bucket/keys-backup-$(date +%Y%m%d).json
```

### Pros & Cons

✅ **Pros:**
- Zero infrastructure needed
- Simple to use
- Git-friendly (file is ignored)
- Audit trail in `.keys.json`
- Direct GCP integration

❌ **Cons:**
- Single file = single point of failure (backup required)
- No multi-user management (file conflicts)
- Manual sync needed after changes

---

## Option 2: Admin API Endpoints

**Best for:** Medium teams (20-100 users), need programmatic access

### Implementation Overview

Add admin endpoints to your MCP server:

```python
# Admin endpoints (protected by admin key)
POST   /admin/keys              # Generate new key
GET    /admin/keys              # List all keys
DELETE /admin/keys/{key_id}     # Revoke key
GET    /admin/keys/{key_id}     # Get key details
```

### How It Works

1. **Initial Setup:**
   - Create one admin key manually: `python scripts/manage_keys.py generate --name "Admin"`
   - Set as environment variable: `MCP_ADMIN_KEY=mcp_admin_xxx`

2. **Daily Usage:**
   ```bash
   # Generate key via API
   curl -X POST https://your-mcp.run.app/admin/keys \
     -H "X-Admin-Key: mcp_admin_xxx" \
     -H "Content-Type: application/json" \
     -d '{"name": "Alice Smith"}'

   # Returns: {"key_id": "a1b2", "key": "mcp_xxx", "name": "Alice Smith"}
   ```

3. **Storage:**
   - Keys stored in GCP Firestore/Cloud SQL
   - Auto-sync to Secret Manager on changes

### Pros & Cons

✅ **Pros:**
- Programmable (can build web UI)
- Multi-user friendly
- Auto-sync to GCP
- Can add usage tracking

❌ **Cons:**
- Requires database setup
- More complex implementation
- Need to secure admin endpoints

---

## Option 3: Database-Backed Management (Enterprise)

**Best for:** Large teams (100+ users), compliance requirements

### Architecture

```
┌──────────────────┐
│  Admin Web UI    │
└────────┬─────────┘
         │
         ↓
┌──────────────────┐
│  Key Management  │
│  Service (API)   │
└────────┬─────────┘
         │
         ↓
┌──────────────────┐    Sync    ┌──────────────────┐
│  Cloud Firestore │─────────────>│ Secret Manager  │
│  (Key Database)  │             │ (Active Keys)   │
└──────────────────┘             └──────────────────┘
```

### Features

- Web UI for key management
- Role-based access control (RBAC)
- Key usage analytics
- Automatic rotation
- Audit logs
- Team/project hierarchies

### Implementation

Would require building:
1. Key management service (Go/Python)
2. Web admin UI (React/Vue)
3. Firestore schema
4. Background job for Secret Manager sync

---

## Recommendation by Team Size

| Team Size | Recommended Option |
|-----------|-------------------|
| 1-20 users | **Option 1: CLI Tool** ⭐ |
| 20-100 users | Option 2: Admin API |
| 100+ users | Option 3: Database-backed |

---

## Security Best Practices

### Key Distribution

**❌ BAD:**
- Slack messages
- Email (unless encrypted)
- GitHub issues
- Shared documents

**✅ GOOD:**
- 1Password shared vault
- LastPass secure notes
- Encrypted email (PGP)
- In-person handoff
- Password-protected files

### Key Rotation

**Schedule:**
- Personal keys: Every 90 days
- Service accounts: Every 180 days
- Compromised keys: Immediately

**Process:**
```bash
# 1. Generate new key
python scripts/manage_keys.py generate --name "Alice Smith (2026-Q2)"

# 2. Share with user
# 3. After user confirms switch, revoke old key
python scripts/manage_keys.py revoke old_key_id

# 4. Sync to GCP
python scripts/manage_keys.py sync-to-gcp
```

### Monitoring

**Track in Cloud Run logs:**
- Failed authentication attempts
- Key usage patterns
- Suspicious activity

**Example query:**
```
resource.type="cloud_run_revision"
jsonPayload.auth_result="failed"
```

---

## FAQ

### Q: How many keys can I have?

A: The CLI tool has no limit. Secret Manager has a 64KB limit per secret, which allows ~500-1000 keys.

### Q: Can I have multiple admin users?

A: With the CLI tool, yes - just share the `.keys.json` file securely (e.g., via git-crypt or encrypted storage).

### Q: What if I lose `.keys.json`?

A: If you have keys in GCP Secret Manager, you can reconstruct it:
```bash
gcloud secrets versions access latest --secret=mcp-api-keys
```
However, you'll lose key metadata (names, creation dates). **Always backup `.keys.json`!**

### Q: Can I use this with CI/CD?

A: Yes! Generate a key for your CI system:
```bash
python scripts/manage_keys.py generate --name "GitHub Actions"
```
Store as GitHub secret and use in workflows.

### Q: How do I migrate from CLI to Admin API?

A: The CLI tool's `.keys.json` can be imported into a database. We can build a migration script if needed.

---

## Example Workflows

### Onboarding a new team member

```bash
# 1. Generate key
python scripts/manage_keys.py generate --name "Alice Smith"

# 2. Save key to 1Password
# 3. Share 1Password item with Alice
# 4. Sync to GCP
python scripts/manage_keys.py sync-to-gcp

# 5. Send Alice setup instructions
# (See CLIENT_SETUP.md)
```

### Offboarding a team member

```bash
# 1. Revoke their key
python scripts/manage_keys.py revoke alice_key_id

# 2. Sync to GCP (takes effect immediately)
python scripts/manage_keys.py sync-to-gcp

# 3. Verify in Cloud Run logs that key is no longer working
```

### Emergency key rotation (compromise)

```bash
# 1. Revoke ALL keys
python scripts/manage_keys.py list  # Get all key IDs
# Revoke each one

# 2. Generate new keys for all users
python scripts/manage_keys.py generate --name "User 1 (emergency rotation)"
# Repeat for all users

# 3. Sync to GCP
python scripts/manage_keys.py sync-to-gcp

# 4. Notify all users via secure channel
# 5. Monitor logs for old key usage attempts
```

---

## Implementation Status

- ✅ **Option 1: CLI Tool** - Implemented and ready to use
- ⏳ **Option 2: Admin API** - Not implemented (can add if needed)
- ⏳ **Option 3: Database-backed** - Not implemented (enterprise feature)

---

## Next Steps

1. Try the CLI tool:
   ```bash
   python scripts/manage_keys.py generate --name "Test User"
   python scripts/manage_keys.py list
   ```

2. Set up GCP sync:
   ```bash
   gcloud auth login
   python scripts/manage_keys.py sync-to-gcp
   ```

3. Share keys with your team

4. Add to your deployment process
