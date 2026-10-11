FROM python:3.11-slim

LABEL maintainer="Neo Team"
LABEL description="Neo: Semantic Multi-Developer Coordination Engine with NVIDIA NIM Support"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create .devsync directory for activity logs
RUN mkdir -p .devsync

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV NEO_MULTITENANCY=false
ENV CLAUDE_TENANT_ID=default
ENV LOG_LEVEL=INFO
ENV NEO_MCP_HOST=0.0.0.0
ENV NEO_MCP_PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# MCP server exposes port 8000
EXPOSE 8000

# Start Neo MCP server
ENTRYPOINT ["python3", "-m", "ide.mcp_neo_server"]

# Health check script (optional debugging)
# Usage: docker run neo --help
