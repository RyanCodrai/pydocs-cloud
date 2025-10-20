# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /srv

# Set PYTHONPATH
ENV PYTHONPATH="/srv" \
    PYTHONUNBUFFERED=1

# Copy dependency files
COPY pyproject.toml uv.lock ./

# ============================================
# Development dependencies
# ============================================
FROM base AS development-deps

# Install system dependencies + dev tools
RUN apt-get update && apt-get install -y make && rm -rf /var/lib/apt/lists/*

# Install ALL dependencies globally (including dev)
RUN uv pip install --system -r pyproject.toml

# ============================================
# Production dependencies
# ============================================
FROM base AS production-deps

# Install ONLY production dependencies globally (no dev deps)
RUN uv pip install --system --no-dev -r pyproject.toml

# ============================================
# Final stage (merge point)
# ============================================
FROM ${BUILD_TARGET:-development-deps} AS final

# Create non-root user
RUN adduser --quiet --disabled-password \
    --home /home/appuser \
    --shell /bin/bash appuser

# Copy application code
COPY . /srv

# Change ownership
RUN chown -R appuser:appuser /srv

# Switch to non-root user
USER appuser

EXPOSE 8080

CMD ["uvicorn", "src.main:application", "--host", "0.0.0.0", "--port", "8080"]
