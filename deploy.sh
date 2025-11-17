#!/bin/bash
# Production deployment for Replit Autoscale
# Optimized for 100+ concurrent users with flexible configuration

echo "==================================================="
echo "TraitorTrack - Production Deployment"
echo "Optimized for 100+ concurrent users"
echo "==================================================="

# Verify CRITICAL environment variables (required for security)
if [ -z "$SESSION_SECRET" ]; then
    echo "❌ ERROR: SESSION_SECRET not set"
    echo "   Generate one with: python3 -c 'import secrets; print(secrets.token_hex(32))'"
    exit 1
fi

if [ -z "$ADMIN_PASSWORD" ]; then
    echo "❌ ERROR: ADMIN_PASSWORD not set"
    echo "   Set a secure admin password in deployment secrets"
    exit 1
fi

# Database Configuration (flexible for Replit built-in PostgreSQL or external)
if [ -n "$PRODUCTION_DATABASE_URL" ]; then
    echo "✅ Using PRODUCTION_DATABASE_URL for database connection"
    export DATABASE_URL="$PRODUCTION_DATABASE_URL"
elif [ -n "$DATABASE_URL" ]; then
    echo "✅ Using Replit built-in PostgreSQL (DATABASE_URL)"
else
    echo "❌ ERROR: No database configured"
    echo "   Set DATABASE_URL (for Replit PostgreSQL) or PRODUCTION_DATABASE_URL (for external DB)"
    exit 1
fi

# Redis Configuration (optional - app works without it using signed cookie sessions)
if [ -n "$REDIS_URL" ]; then
    echo "✅ Redis configured - multi-worker cache coherence enabled"
else
    echo "⚠️  Redis not configured - using signed cookie sessions (Autoscale-compatible)"
    echo "   This is perfectly fine for Replit Autoscale deployments"
    echo "   Rate limiting will be per-worker (still functional)"
fi

echo ""
echo "✅ Environment configuration verified"
echo "✅ Starting Gunicorn with gevent workers for production"
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
