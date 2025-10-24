#!/bin/bash
# Simplified production deployment for Replit
# No virtual environment needed - Replit handles packages via requirements.txt

echo "==================================================="
echo "TraceTrack - Production Deployment"
echo "Optimized for 100+ concurrent users"
echo "==================================================="

# Verify required environment variables
if [ -z "$SESSION_SECRET" ]; then
    echo "❌ ERROR: SESSION_SECRET not set"
    exit 1
fi

if [ -z "$ADMIN_PASSWORD" ]; then
    echo "❌ ERROR: ADMIN_PASSWORD not set"
    exit 1
fi

if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL not set"
    exit 1
fi

echo "✅ Environment variables verified"
echo "✅ Starting Gunicorn with gevent workers"
echo ""

# Use PORT environment variable for Cloud Run compatibility (defaults to 5000 for local dev)
PORT=${PORT:-5000}

# Start Gunicorn with production settings
# Reduced workers for Cloud Run autoscale to avoid resource exhaustion
exec gunicorn \
  --bind 0.0.0.0:$PORT \
  --workers 2 \
  --worker-class gevent \
  --worker-connections 500 \
  --timeout 120 \
  --keep-alive 5 \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  --log-level info \
  --access-logfile - \
  --error-logfile - \
  --preload \
  main:app
