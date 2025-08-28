#!/bin/bash
# Production server with 4 workers for optimal performance

echo "Starting TraceTrack with 4-worker configuration..."
echo "This configuration provides optimal performance for 20+ concurrent users"
echo "=================================================="

# Kill any existing gunicorn processes
pkill -f gunicorn 2>/dev/null

# Start with 4 workers
gunicorn --bind 0.0.0.0:5000 \
         --workers 4 \
         --timeout 60 \
         --max-requests 2000 \
         --max-requests-jitter 100 \
         --reuse-port \
         --access-logfile - \
         --error-logfile - \
         main:app