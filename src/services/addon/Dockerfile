# Build stage
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Copy shared dependencies
COPY src/shared /app/shared

# Copy service files
COPY src/services/addon /app/addon

# Install dependencies
WORKDIR /app/addon
RUN uv pip install --system -e .

# Runtime stage
FROM python:3.12-slim

WORKDIR /app

# Copy Python dependencies and shared modules from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /app/shared /app/shared
COPY --from=builder /app/addon /app/addon

WORKDIR /app/addon

# Set Python path to include shared module
ENV PYTHONPATH=/app:$PYTHONPATH

# Expose API port
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8003/health')" || exit 1

# Default command (can be overridden for worker)
CMD ["python", "main.py"]
