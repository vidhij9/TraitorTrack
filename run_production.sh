#!/bin/bash

# Production startup script for TraceTrack
# Optimized for 20+ concurrent users with heavy operations

echo "Starting TraceTrack in production mode..."

# Set environment variables
export ENVIRONMENT="production"
export FLASK_ENV="production"
export PYTHONUNBUFFERED=1

# Kill any existing gunicorn processes
pkill -f gunicorn 2>/dev/null || true
sleep 2

# Start with optimized configuration
# 4 workers × 2 threads = 8 concurrent handlers
# Handles 20+ concurrent users with intensive operations
exec gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 4 \
    --threads 2 \
    --worker-class gthread \
    --worker-connections 1000 \
    --timeout 60 \
    --graceful-timeout 30 \
    --keepalive 5 \
    --max-requests 2000 \
    --max-requests-jitter 100 \
    --preload \
    --access-logfile - \
    --error-logfile - \
    --log-level warning \
    --capture-output \
    --enable-stdio-inheritance \
    main:app