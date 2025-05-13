#!/bin/bash

# Production-ready server script for TraceTrack application
# Optimized for 100+ concurrent users

echo "Starting TraceTrack server with high concurrency configuration..."

# Use gevent worker class for async request handling
# Calculate optimal number of workers based on CPU cores
WORKERS=$(($(nproc) * 2 + 1))
echo "Using $WORKERS workers based on available CPU cores"

# Start Gunicorn with optimized settings
exec gunicorn \
    --worker-class=gevent \
    --workers=$WORKERS \
    --threads=2 \
    --bind=0.0.0.0:5000 \
    --timeout=30 \
    --keep-alive=5 \
    --max-requests=1000 \
    --max-requests-jitter=100 \
    --log-level=info \
    --access-logfile=- \
    --error-logfile=- \
    --reload \
    main:app