#!/bin/bash
cd /home/javiator/work/projects/tenant-management/tenant-management-java-app/backend-mcp-uv
exec /home/javiator/.local/bin/uv run python -m backend_mcp_uv "$@"
