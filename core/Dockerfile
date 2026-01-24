# ===================================
# Alfred AI Service Dockerfile
# ===================================
# Multi-stage build for optimized production image

# ===================================
# Stage 1: Builder
# ===================================
FROM python:3.12-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
ENV UV_HOME=/opt/uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/ && \
    mv /root/.local/bin/uvx /usr/local/bin/

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (without dev dependencies for production)
# --frozen ensures the lock file is used without modification
# --no-dev excludes development dependencies
RUN uv sync --frozen --no-dev

# ===================================
# Stage 2: Runtime
# ===================================
FROM python:3.12-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 alfred && \
    mkdir -p /app && \
    chown -R alfred:alfred /app

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=alfred:alfred . .

# Switch to non-root user
USER alfred

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
