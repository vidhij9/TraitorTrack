#!/bin/bash
# Production deployment for Replit Autoscale
# CRITICAL: Opens port 5000 IMMEDIATELY, runs migrations in background
# Designed for 100+ concurrent users with zero-downtime startup

echo "==================================================="
echo "TraitorTrack - Fast Production Deployment"
echo "Port 5000 opens IMMEDIATELY - migrations run in background"
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
fi

echo ""
echo "✅ Environment configuration verified"
echo ""

# Always use port 5000 for Replit Autoscale deployment
PORT=5000

# ==================================================================================
# FAST STARTUP STRATEGY:
# 1. Start Gunicorn IMMEDIATELY (no --preload to avoid blocking)
# 2. The app has early health endpoints that respond before heavy init
# 3. Migrations run in background via the app's lazy initialization
# ==================================================================================

echo "🚀 Starting Gunicorn NOW (port $PORT) - migrations handled by app"
echo ""

# Start Gunicorn with fast-startup settings
# Key changes for fast port binding:
# - REMOVED --preload (was loading app before forking, blocking port)
# - Workers will lazy-load app on first request
# - Early health endpoints (/health, /ready) respond immediately
exec gunicorn \
  --bind 0.0.0.0:$PORT \
  --workers ${GUNICORN_WORKERS:-2} \
  --worker-class gevent \
  --worker-connections 500 \
  --timeout ${GUNICORN_TIMEOUT:-120} \
  --graceful-timeout 30 \
  --keep-alive 5 \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  --log-level info \
  --access-logfile - \
  --error-logfile - \
  main:app
