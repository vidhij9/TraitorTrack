#!/bin/bash

# TraceTrack Optimized Startup Script
# Supports 20+ concurrent users with multi-worker configuration

echo "=========================================="
echo "Starting TraceTrack - Optimized for 20+ concurrent users"
echo "Configuration: 4 workers × 2 threads = 8 concurrent handlers"
echo "=========================================="

# Use optimized gunicorn configuration for production
exec gunicorn \
  --bind 0.0.0.0:5000 \
  --workers 4 \
  --threads 2 \
  --worker-class gthread \
  --timeout 60 \
  --keepalive 5 \
  --max-requests 2000 \
  --max-requests-jitter 200 \
  --reuse-port \
  --access-logfile - \
  --error-logfile - \
  --log-level info \
  main:app