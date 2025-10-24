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

# Start Gunicorn with production settings
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
