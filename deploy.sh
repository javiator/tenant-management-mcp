#!/bin/bash
# Deployment script for TM MCP Server to Google Cloud Run
#
# Usage:
#   ./deploy.sh                    # Deploy to default project
#   ./deploy.sh --project my-proj  # Deploy to specific project
#   ./deploy.sh --help             # Show help

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default configuration
PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="tm-mcp-server"
IMAGE_NAME="tm-mcp"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --project)
      PROJECT_ID="$2"
      shift 2
      ;;
    --region)
      REGION="$2"
      shift 2
      ;;
    --service-name)
      SERVICE_NAME="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo ""
      echo "Options:"
      echo "  --project PROJECT_ID    GCP project ID (default: \$GCP_PROJECT_ID)"
      echo "  --region REGION         GCP region (default: us-central1)"
      echo "  --service-name NAME     Cloud Run service name (default: tm-mcp-server)"
      echo "  --help                  Show this help message"
      echo ""
      echo "Environment variables:"
      echo "  GCP_PROJECT_ID          Default GCP project ID"
      echo "  GCP_REGION              Default GCP region"
      echo ""
      echo "Example:"
      echo "  ./deploy.sh --project my-project --region europe-west1"
      exit 0
      ;;
    *)
      echo -e "${RED}Error: Unknown option $1${NC}"
      echo "Run with --help for usage information"
      exit 1
      ;;
  esac
done

# Validate prerequisites
if [ -z "$PROJECT_ID" ]; then
  echo -e "${RED}Error: GCP project ID not set${NC}"
  echo "Set it via:"
  echo "  - Environment variable: export GCP_PROJECT_ID=your-project-id"
  echo "  - Command line: ./deploy.sh --project your-project-id"
  exit 1
fi

echo -e "${GREEN}=== TM MCP Server Deployment ===${NC}"
echo ""
echo "Configuration:"
echo "  Project:      $PROJECT_ID"
echo "  Region:       $REGION"
echo "  Service:      $SERVICE_NAME"
echo "  Image:        gcr.io/$PROJECT_ID/$IMAGE_NAME"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI not found${NC}"
    echo "Install from: https://cloud.google.com/sdk/install"
    exit 1
fi

# Verify gcloud authentication
echo -e "${YELLOW}Checking gcloud authentication...${NC}"
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${YELLOW}Not authenticated. Running gcloud auth login...${NC}"
    gcloud auth login
fi

# Set project
echo -e "${YELLOW}Setting GCP project to $PROJECT_ID...${NC}"
gcloud config set project "$PROJECT_ID"

# Enable required APIs
echo -e "${YELLOW}Ensuring required APIs are enabled...${NC}"
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  containerregistry.googleapis.com \
  secretmanager.googleapis.com

# Check if secrets exist
echo -e "${YELLOW}Checking for required secrets...${NC}"
MISSING_SECRETS=()

if ! gcloud secrets describe mcp-api-keys &> /dev/null; then
    echo -e "${YELLOW}⚠️  Secret 'mcp-api-keys' not found${NC}"
    MISSING_SECRETS+=("mcp-api-keys")
fi

if ! gcloud secrets describe backend-token &> /dev/null; then
    echo -e "${YELLOW}⚠️  Secret 'backend-token' not found (optional)${NC}"
fi

if [ ${#MISSING_SECRETS[@]} -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}Missing secrets detected. Create them with:${NC}"
    for secret in "${MISSING_SECRETS[@]}"; do
        echo "  echo 'your-value' | gcloud secrets create $secret --data-file=-"
    done
    echo ""
    echo "Or use the key management script:"
    echo "  uv run python scripts/manage_keys.py generate --name 'User'"
    echo "  uv run python scripts/manage_keys.py sync-to-gcp"
    echo ""
    read -p "Continue without secrets (authentication disabled)? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Build and push image
echo ""
echo -e "${GREEN}Step 1: Building and pushing Docker image${NC}"
echo -e "${YELLOW}Running: gcloud builds submit${NC}"

gcloud builds submit \
  --tag "gcr.io/$PROJECT_ID/$IMAGE_NAME" \
  --timeout=10m

echo -e "${GREEN}✅ Image built and pushed successfully${NC}"

# Deploy to Cloud Run
echo ""
echo -e "${GREEN}Step 2: Deploying to Cloud Run${NC}"
echo -e "${YELLOW}Running: gcloud run deploy${NC}"

# Build deploy command
DEPLOY_CMD="gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$IMAGE_NAME \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --port 8000 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --min-instances 0"

# Add secrets if they exist
if gcloud secrets describe mcp-api-keys &> /dev/null; then
    DEPLOY_CMD="$DEPLOY_CMD --set-secrets MCP_API_KEYS=mcp-api-keys:latest"
fi

if gcloud secrets describe backend-token &> /dev/null; then
    DEPLOY_CMD="$DEPLOY_CMD --set-secrets BACKEND_MCP_API_TOKEN=backend-token:latest"
fi

# Prompt for backend URL
read -p "Enter backend URL (or press Enter for http://localhost:8080): " BACKEND_URL
BACKEND_URL=${BACKEND_URL:-http://localhost:8080}

DEPLOY_CMD="$DEPLOY_CMD --set-env-vars BACKEND_MCP_BASE_URL=$BACKEND_URL"

# Execute deployment
eval $DEPLOY_CMD

echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --region $REGION \
  --format 'value(status.url)')

echo ""
echo -e "${GREEN}=== Deployment Summary ===${NC}"
echo "Service URL:  $SERVICE_URL"
echo "Region:       $REGION"
echo "Project:      $PROJECT_ID"
echo ""
echo -e "${GREEN}Test your deployment:${NC}"
echo "  # Without authentication (will fail if auth enabled)"
echo "  curl $SERVICE_URL/health"
echo ""
echo "  # With authentication"
echo "  curl -H \"X-API-Key: your-key\" $SERVICE_URL/health"
echo ""
echo -e "${GREEN}View logs:${NC}"
echo "  gcloud run services logs read $SERVICE_NAME --region $REGION"
echo ""
echo -e "${GREEN}Update configuration:${NC}"
echo "  gcloud run services update $SERVICE_NAME --region $REGION"
echo ""
