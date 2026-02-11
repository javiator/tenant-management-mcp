# Multi-stage Dockerfile for TM MCP Server
# Optimized for Cloud Run deployment

# Stage 1: Build stage
FROM python:3.11-slim AS builder

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files first (for better layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies in a virtual environment
RUN uv sync --frozen --no-dev

# Stage 2: Runtime stage
FROM python:3.11-slim

# Install uv in runtime stage
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create non-root user for security
RUN useradd -m -u 1000 mcpuser && \
    mkdir -p /app && \
    chown -R mcpuser:mcpuser /app

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=mcpuser:mcpuser /app/.venv /app/.venv

# Copy application source code
COPY --chown=mcpuser:mcpuser pyproject.toml uv.lock ./
COPY --chown=mcpuser:mcpuser src ./src

# Switch to non-root user
USER mcpuser

# Add .venv to PATH so we can run commands directly
ENV PATH="/app/.venv/bin:$PATH"

# Expose port 8000 (Cloud Run default)
EXPOSE 8000

# Health check (optional but recommended)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=2)" || exit 1

# Run the MCP server with streamable-http transport
# Cloud Run will inject PORT environment variable (defaults to 8000)
CMD ["uv", "run", "tm-mcp", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]
