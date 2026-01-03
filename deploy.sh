#!/bin/bash
# Production deployment for Replit Autoscale
# Runs schema sync check and migrations FIRST, then starts server on port 5000
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
# Keep both DATABASE_URL and PRODUCTION_DATABASE_URL for sync checking
if [ -n "$PRODUCTION_DATABASE_URL" ]; then
    echo "✅ Using PRODUCTION_DATABASE_URL for production database connection"
else
    echo "❌ ERROR: PRODUCTION_DATABASE_URL not configured"
    echo "   Set PRODUCTION_DATABASE_URL for production database connection"
    exit 1
fi

# Save original DATABASE_URL for sync comparison (if different from production)
ORIGINAL_DATABASE_URL="$DATABASE_URL"
if [ -n "$DATABASE_URL" ] && [ "$DATABASE_URL" != "$PRODUCTION_DATABASE_URL" ]; then
    echo "✅ Development DATABASE_URL available for sync verification"
else
    echo "⚠️  No separate development DATABASE_URL for sync verification"
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
# STEP 1: SCHEMA SYNC CHECK (verify database alignment)
# This ensures dev and production schemas are in sync before deployment
# ==================================================================================

echo "🔍 Checking database schema sync status..."
echo ""

# Run sync check if both DATABASE_URL and PRODUCTION_DATABASE_URL are set
if [ -n "$DATABASE_URL" ] && [ -n "$PRODUCTION_DATABASE_URL" ]; then
    timeout 60 python check_db_sync.py --json > /tmp/sync_check_result.json 2>&1
    SYNC_EXIT_CODE=$?
    
    if [ $SYNC_EXIT_CODE -eq 0 ]; then
        echo "✅ Database schemas are IN SYNC"
        echo ""
    elif [ $SYNC_EXIT_CODE -eq 1 ]; then
        echo "⚠️  Database schemas are OUT OF SYNC"
        echo "   Migrations will be applied to bring production up to date"
        echo ""
        
        # Parse and display sync details
        if [ -f /tmp/sync_check_result.json ]; then
            DEV_REV=$(python3 -c "import json; d=json.load(open('/tmp/sync_check_result.json')); print(d.get('alembic',{}).get('dev_revision','unknown'))" 2>/dev/null || echo "unknown")
            PROD_REV=$(python3 -c "import json; d=json.load(open('/tmp/sync_check_result.json')); print(d.get('alembic',{}).get('prod_revision','unknown'))" 2>/dev/null || echo "unknown")
            echo "   Development revision: $DEV_REV"
            echo "   Production revision:  $PROD_REV"
            echo ""
        fi
    else
        echo "⚠️  WARNING: Sync check failed (exit code $SYNC_EXIT_CODE)"
        echo "   Continuing with migrations..."
        echo ""
    fi
else
    echo "⚠️  Skipping sync check (need both DATABASE_URL and PRODUCTION_DATABASE_URL)"
    echo ""
fi

# ==================================================================================
# STEP 2: RUN MIGRATIONS (with timeout to prevent hanging)
# This ensures database schema is up-to-date before accepting traffic
# ==================================================================================

echo "📦 Running database migrations..."
echo ""

# Set DATABASE_URL to production for migrations
export DATABASE_URL="$PRODUCTION_DATABASE_URL"

# Run migrations with 300 second timeout (5 minutes for large tables)
timeout 300 python run_production_migrations.py
MIGRATION_EXIT_CODE=$?

if [ $MIGRATION_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ Database migrations completed successfully"
    echo ""
elif [ $MIGRATION_EXIT_CODE -eq 124 ]; then
    echo ""
    echo "❌ FATAL: Migration timed out after 300 seconds"
    echo "   Cannot start server with potentially stale schema"
    echo "   Please check database connectivity and migration logs"
    exit 1
else
    echo ""
    echo "❌ FATAL: Migration failed with exit code $MIGRATION_EXIT_CODE"
    echo "   Cannot start server with potentially stale schema"
    echo "   Please fix migration issues before deployment"
    exit 1
fi

# ==================================================================================
# STEP 2.5: ENSURE INDEX SYNC (catches any indexes not in migrations)
# This is a safety net to ensure production has all required indexes
# ==================================================================================

timeout 120 python ensure_indexes.py 2>&1 || echo "⚠️  Index verification completed with warnings"
echo ""

# ==================================================================================
# STEP 3: POST-MIGRATION SYNC VERIFICATION
# Verify schemas are now in sync after migrations
# ==================================================================================

# Restore DATABASE_URL for sync verification if we have a separate dev database
if [ -n "$ORIGINAL_DATABASE_URL" ] && [ "$ORIGINAL_DATABASE_URL" != "$PRODUCTION_DATABASE_URL" ]; then
    export DATABASE_URL="$ORIGINAL_DATABASE_URL"
    
    echo "🔍 Verifying post-migration sync status..."
    timeout 30 python check_db_sync.py 2>&1 | head -20
    POST_SYNC_CODE=$?
    
    if [ $POST_SYNC_CODE -eq 0 ]; then
        echo ""
        echo "✅ Post-migration: Databases are IN SYNC"
    else
        echo ""
        echo "⚠️  Post-migration: Databases may still differ (non-critical)"
    fi
    echo ""
else
    echo "⚠️  Skipping post-migration sync verification (no separate dev database)"
    echo ""
fi

# ==================================================================================
# STEP 4: START GUNICORN SERVER
# ==================================================================================

# Ensure DATABASE_URL points to production for the running application
export DATABASE_URL="$PRODUCTION_DATABASE_URL"

# Use PORT environment variable from Replit Autoscale, fallback to 5000 for local dev
# Autoscale provides a dynamic PORT that MUST be used for the health check to pass
APP_PORT="${PORT:-5000}"

echo "🚀 Starting Gunicorn on port $APP_PORT"
echo ""

exec gunicorn \
  --bind 0.0.0.0:$APP_PORT \
  --workers ${GUNICORN_WORKERS:-2} \
  --worker-class gevent \
  --worker-connections 500 \
  --timeout ${GUNICORN_TIMEOUT:-1200} \
  --graceful-timeout 30 \
  --keep-alive 5 \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  --log-level info \
  --access-logfile - \
  --error-logfile - \
  main:app
