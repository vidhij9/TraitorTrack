#!/bin/bash
# Production deployment for Replit Autoscale
# Runs migrations FIRST, then starts server on port 5000
# Designed for 100+ concurrent users with reliable database schema

echo "==================================================="
echo "TraitorTrack - Production Deployment"
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

# ==================================================================================
# STEP 1: RUN MIGRATIONS (with timeout to prevent hanging)
# This ensures database schema is up-to-date before accepting traffic
# ==================================================================================

echo "📦 Running database migrations..."
echo ""

# Run migrations with 60 second timeout
timeout 60 python run_production_migrations.py
MIGRATION_EXIT_CODE=$?

if [ $MIGRATION_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ Database migrations completed successfully"
    echo ""
elif [ $MIGRATION_EXIT_CODE -eq 124 ]; then
    echo ""
    echo "⚠️  WARNING: Migration timed out after 60 seconds"
    echo "⚠️  Continuing with server startup - migrations may still be running"
    echo ""
else
    echo ""
    echo "⚠️  WARNING: Migration script exited with code $MIGRATION_EXIT_CODE"
    echo "⚠️  Continuing with server startup - check logs for details"
    echo ""
fi

# ==================================================================================
# STEP 2: START GUNICORN SERVER
# ==================================================================================

# Always use port 5000 for Replit Autoscale deployment
PORT=5000

echo "🚀 Starting Gunicorn on port $PORT"
echo ""

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
