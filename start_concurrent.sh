#!/bin/bash

# Start TraceTrack with optimized configuration for 20+ concurrent users
# This configuration provides:
# - 4 workers × 2 threads = 8 concurrent request handlers
# - Threaded workers for better session management  
# - Optimized for scanning operations

echo "Starting TraceTrack with concurrent user optimization..."
echo "Configuration: 4 workers × 2 threads = 8 concurrent handlers"

gunicorn \
  --bind 0.0.0.0:5000 \
  --workers 4 \
  --threads 2 \
  --worker-class gthread \
  --timeout 60 \
  --keepalive 5 \
  --max-requests 2000 \
  --max-requests-jitter 200 \
  --reuse-port \
  --reload \
  --access-logfile - \
  --error-logfile - \
  --log-level info \
  main:app