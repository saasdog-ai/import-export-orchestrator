# Build for linux/amd64 platform (required for ECS Fargate)
FROM --platform=linux/amd64 python:3.11-slim

WORKDIR /app

# Cloud provider extras: aws, azure, gcp, or cloud (all providers)
ARG CLOUD_EXTRAS=aws

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Copy application code (needed for editable install)
COPY app/ ./app/

# Install Python dependencies with selected cloud provider extras
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[${CLOUD_EXTRAS}]"

# Copy startup script (before switching user)
COPY scripts/start.sh /app/start.sh

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app && chmod +x /app/start.sh
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5)"

# Run the application (migrations will run automatically on startup)
CMD ["/app/start.sh"]

