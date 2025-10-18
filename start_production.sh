#!/bin/bash
# Production deployment script for TraceTrack
# Optimized for Replit Autoscale Deployment

echo "Starting TraceTrack in PRODUCTION mode..."
echo "Gunicorn with gevent workers for high concurrency"
echo "=================================================="

# Production Gunicorn configuration for 100+ concurrent users
exec gunicorn \
  --bind 0.0.0.0:5000 \
  --workers 4 \
  --worker-class gevent \
  --worker-connections 1000 \
  --timeout 120 \
  --keep-alive 5 \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  --log-level info \
  --access-logfile - \
  --error-logfile - \
  --preload \
  main:app