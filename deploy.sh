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
echo ""

# ==================================================================================
# PRE-DEPLOYMENT: Fast migration check with timeout
# ==================================================================================
# Migrations are designed to be idempotent. Skip if we can verify schema is ready.
# Use timeout to prevent blocking port 5000 opening (Autoscale requirement).
# ==================================================================================
MIGRATION_TIMEOUT=${MIGRATION_TIMEOUT:-15}  # Default 15 second timeout

echo "🔄 Checking database migrations (timeout: ${MIGRATION_TIMEOUT}s)..."

# Run migrations with timeout to prevent blocking deployment
if command -v timeout &> /dev/null; then
    timeout ${MIGRATION_TIMEOUT} python run_migrations.py
    MIGRATION_EXIT_CODE=$?
else
    # Fallback if timeout command not available
    python run_migrations.py &
    MIGRATION_PID=$!
    
    # Wait with manual timeout
    COUNTER=0
    while kill -0 $MIGRATION_PID 2>/dev/null && [ $COUNTER -lt $MIGRATION_TIMEOUT ]; do
        sleep 1
        COUNTER=$((COUNTER + 1))
    done
    
    if kill -0 $MIGRATION_PID 2>/dev/null; then
        echo "⚠️  Migration timed out after ${MIGRATION_TIMEOUT}s - killing process"
        kill $MIGRATION_PID 2>/dev/null
        MIGRATION_EXIT_CODE=124
    else
        wait $MIGRATION_PID
        MIGRATION_EXIT_CODE=$?
    fi
fi

case $MIGRATION_EXIT_CODE in
    0)
        echo "✅ Database migrations completed successfully"
        ;;
    124)
        echo "⚠️  Migration timed out - starting server anyway (schema likely up-to-date)"
        ;;
    *)
        echo "⚠️  Migration exited with code $MIGRATION_EXIT_CODE - starting server anyway"
        ;;
esac

echo ""
echo "✅ Starting Gunicorn with gevent workers for production"
echo ""

# Use PORT environment variable for Cloud Run compatibility (defaults to 5000 for local dev)
PORT=${PORT:-5000}

# Start Gunicorn with optimized production settings
# - Fast startup: reduced timeout, preload, minimal workers
# - Autoscale-ready: stateless, health-check compatible
# - gevent for async I/O performance
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
  --preload \
  main:app
