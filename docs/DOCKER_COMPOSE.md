# Docker Compose Guide

Complete guide for running TM MCP Server with Docker Compose.

## Why Docker Compose?

✅ **Better than plain Docker:**
- Single command to start/stop everything
- Environment configuration via `.env` files
- Easy to add related services (database, redis, etc.)
- Volume management simplified
- Network isolation automatic
- Better for local development

---

## Quick Start

### 1. Generate API Keys (Optional)

```bash
# Generate test keys
uv run python scripts/manage_keys.py generate --name "Dev User"

# Export for use in Docker
uv run python scripts/manage_keys.py export
```

### 2. Configure Environment

```bash
# Copy template
cp .env.docker .env.local

# Edit with your settings
nano .env.local
```

**Example `.env.local`:**
```bash
BACKEND_MCP_BASE_URL=http://host.docker.internal:8080
MCP_API_KEYS=mcp_xxx,mcp_yyy
```

### 3. Start the Server

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

### 4. Test

```bash
# Health check
curl http://localhost:8000/health

# With API key (if configured)
curl -H "Authorization: Bearer mcp_xxx" http://localhost:8000/
```

### 5. Stop

```bash
# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

---

## Common Commands

### Start/Stop

```bash
# Start in background
docker-compose up -d

# Start in foreground (see logs)
docker-compose up

# Stop services
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove everything (including images)
docker-compose down --rmi all -v
```

### Logs

```bash
# View all logs
docker-compose logs

# Follow logs (live tail)
docker-compose logs -f

# Logs for specific service
docker-compose logs mcp-server

# Last 100 lines
docker-compose logs --tail=100
```

### Build

```bash
# Build images
docker-compose build

# Force rebuild (no cache)
docker-compose build --no-cache

# Build and start
docker-compose up --build
```

### Debugging

```bash
# Execute command in running container
docker-compose exec mcp-server bash

# Run one-off command
docker-compose run mcp-server python --version

# Check service status
docker-compose ps

# View resource usage
docker stats tm-mcp-server
```

---

## Configuration

### Environment Variables

Docker Compose loads env vars from these files (in order):

1. `.env` - Default environment (git-ignored)
2. `.env.local` - Local overrides (git-ignored)
3. `.env.docker` - Template (committed to git)

**Priority:** `.env.local` > `.env` > `.env.docker`

### Using API Keys from Key Management

```bash
# Auto-generate .env.local with current keys
cat > .env.local <<EOF
BACKEND_MCP_BASE_URL=http://host.docker.internal:8080
MCP_API_KEYS=$(uv run python scripts/manage_keys.py export)
EOF

# Start with authentication enabled
docker-compose up -d
```

### Development Mode (No Auth)

```bash
# .env.local
BACKEND_MCP_BASE_URL=http://host.docker.internal:8080
MCP_API_KEYS=
```

---

## Profiles

Docker Compose supports profiles for different scenarios:

### Profile: Production-like

```yaml
# docker-compose.prod.yml
services:
  mcp-server:
    image: gcr.io/PROJECT_ID/tm-mcp:latest
    # No source code mounting
    # Stricter resource limits
```

**Usage:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up
```

### Profile: Development with Backend

```yaml
# docker-compose.dev.yml
services:
  mcp-server:
    depends_on:
      - mock-backend

  mock-backend:
    image: your-backend:latest
    ports:
      - "8080:8080"
```

**Usage:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

---

## Volume Management

### Mount Source Code (Development)

Edit `docker-compose.override.yml`:
```yaml
services:
  mcp-server:
    volumes:
      - ./src:/app/src:ro  # Read-only mount
```

This allows you to edit code locally and test in container.

**Note:** You'll need to restart to see changes:
```bash
docker-compose restart mcp-server
```

### Persistent Data (if needed)

```yaml
services:
  mcp-server:
    volumes:
      - mcp-data:/app/data

volumes:
  mcp-data:
    driver: local
```

---

## Networking

### Access Host Services

From container, use `host.docker.internal`:

```bash
# Access backend running on host
BACKEND_MCP_BASE_URL=http://host.docker.internal:8080
```

### Connect Multiple Services

```yaml
services:
  mcp-server:
    networks:
      - mcp-network

  backend:
    networks:
      - mcp-network

networks:
  mcp-network:
    driver: bridge
```

Now services can communicate:
```bash
# mcp-server can reach backend at:
http://backend:8080
```

---

## Health Checks

### Built-in Health Check

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:8000/health', timeout=2)"]
  interval: 30s
  timeout: 3s
  retries: 3
  start_period: 5s
```

### Check Health Status

```bash
# View health status
docker-compose ps

# Output shows:
# tm-mcp-server   Up (healthy)
```

### Wait for Healthy

```yaml
services:
  client:
    depends_on:
      mcp-server:
        condition: service_healthy
```

---

## Resource Limits

### Configure Limits

```yaml
services:
  mcp-server:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

### Monitor Usage

```bash
# Real-time stats
docker stats tm-mcp-server

# Output:
# NAME            CPU %   MEM USAGE / LIMIT
# tm-mcp-server   0.5%    120MB / 512MB
```

---

## Multi-Container Setup

### Example: MCP Server + Backend + Database

```yaml
version: '3.8'

services:
  database:
    image: postgres:15
    environment:
      POSTGRES_DB: tenant_db
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secret
    volumes:
      - db-data:/var/lib/postgresql/data

  backend:
    image: your-backend:latest
    depends_on:
      database:
        condition: service_healthy
    environment:
      DB_HOST: database
      DB_PORT: 5432

  mcp-server:
    build: .
    depends_on:
      backend:
        condition: service_started
    environment:
      BACKEND_MCP_BASE_URL: http://backend:8080

volumes:
  db-data:
```

**Start everything:**
```bash
docker-compose up -d
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs mcp-server

# Common issues:
# - Port 8000 already in use
# - Missing environment variables
# - Backend not reachable
```

**Solution: Port conflict**
```yaml
ports:
  - "8001:8000"  # Use different host port
```

### Can't Connect to Host Services

**Problem:** `connection refused` when accessing `host.docker.internal`

**Solution (Linux):**
```bash
# Add to docker-compose.yml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

### Authentication Not Working

```bash
# Check environment variables are loaded
docker-compose exec mcp-server env | grep MCP_API_KEYS

# If empty, check .env.local exists
ls -la .env.local

# Recreate container to reload env
docker-compose up -d --force-recreate
```

### Build Cache Issues

```bash
# Clear cache and rebuild
docker-compose build --no-cache
docker-compose up -d --force-recreate
```

---

## Best Practices

### Development

```bash
# Use .env.local for local settings
cp .env.docker .env.local

# Mount source code for quick iteration
# (already configured in docker-compose.override.yml)

# Watch logs
docker-compose logs -f

# Fast restart after code changes
docker-compose restart mcp-server
```

### Testing

```bash
# Use separate compose file for tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit

# Run tests in container
docker-compose run mcp-server pytest
```

### Production

```bash
# Use specific compose file
docker-compose -f docker-compose.prod.yml up -d

# Don't mount source code
# Use built image, not build context
# Set resource limits
# Configure restart policies
```

---

## Integration with GCP

### Local → Cloud Workflow

```bash
# 1. Develop locally with Docker Compose
docker-compose up -d

# 2. Test locally
curl http://localhost:8000/

# 3. Build image for Cloud Run
docker build -t gcr.io/PROJECT_ID/tm-mcp .

# 4. Push to GCR
docker push gcr.io/PROJECT_ID/tm-mcp

# 5. Deploy to Cloud Run
gcloud run deploy tm-mcp-server --image gcr.io/PROJECT_ID/tm-mcp
```

### Use Same Image Locally and in Cloud

```yaml
# docker-compose.yml
services:
  mcp-server:
    image: gcr.io/PROJECT_ID/tm-mcp:latest
    # No build: directive
```

**Pull from GCR and run locally:**
```bash
docker-compose pull
docker-compose up -d
```

---

## Examples

### Example 1: Quick Test

```bash
# Start without authentication
echo "MCP_API_KEYS=" > .env.local
docker-compose up -d

# Test
curl http://localhost:8000/

# Stop
docker-compose down
```

### Example 2: With Authentication

```bash
# Generate and export keys
API_KEYS=$(uv run python scripts/manage_keys.py export)

# Configure
cat > .env.local <<EOF
BACKEND_MCP_BASE_URL=http://host.docker.internal:8080
MCP_API_KEYS=$API_KEYS
EOF

# Start
docker-compose up -d

# Test (will require API key)
curl -H "Authorization: Bearer $(echo $API_KEYS | cut -d',' -f1)" http://localhost:8000/
```

### Example 3: Development with Code Mounting

```bash
# Code changes reflected without rebuild
# (using docker-compose.override.yml)

# Edit source code
vim src/tm_mcp/server.py

# Restart to see changes
docker-compose restart mcp-server

# View logs
docker-compose logs -f mcp-server
```

---

## Comparison: Docker vs Docker Compose

| Task | Docker Command | Docker Compose |
|------|----------------|----------------|
| Start | `docker run -d -p 8000:8000 -e VAR=val ...` | `docker-compose up -d` |
| Stop | `docker stop container && docker rm container` | `docker-compose down` |
| Logs | `docker logs -f container` | `docker-compose logs -f` |
| Rebuild | `docker build -t image . && docker stop ...` | `docker-compose up --build` |
| Env vars | Multiple `-e` flags | `.env` file |
| Multiple containers | Multiple `docker run` commands | Single `docker-compose up` |

**Winner:** Docker Compose for development! 🏆

---

## Quick Reference

```bash
# Start
docker-compose up -d

# Logs
docker-compose logs -f

# Stop
docker-compose down

# Rebuild
docker-compose up --build

# Shell
docker-compose exec mcp-server bash

# Status
docker-compose ps
```

---

## Next Steps

- ✅ Configure `.env.local` with your settings
- ✅ Start server: `docker-compose up -d`
- ✅ Test locally
- ✅ Ready to deploy to GCP!

See [DEPLOYMENT.md](DEPLOYMENT.md) for Cloud Run deployment.
