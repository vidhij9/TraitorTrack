# Production-ready multi-stage Dockerfile for TraceTrack
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment and install dependencies
WORKDIR /app
COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    rsync \
    gosu \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 app

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code with proper ownership
COPY --chown=app:app . .

# Create logs directory and make entrypoint script executable
RUN mkdir -p /app/logs && chown -R app:app /app/logs && \
    chmod +x /app/scripts/entrypoint.sh

# Note: We start as root to handle volume permissions, then drop to app user in entrypoint
# USER app will be handled by entrypoint script

# Environment variables for production
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV ENVIRONMENT=production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Expose port
EXPOSE 5000

# Set entrypoint and default command
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["gunicorn", \
    "--config", "/app/gunicorn_config.py", \
    "main:app"]