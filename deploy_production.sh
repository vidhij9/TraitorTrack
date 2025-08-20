#!/bin/bash

# Production Deployment Script for TraceTrack
# Automatically configures and deploys the application for 50+ concurrent users

echo "🚀 TraceTrack Production Deployment Script"
echo "=========================================="

# Set production environment
export FLASK_ENV=production
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

# Database configuration
export DB_POOL_SIZE=50
export DB_MAX_OVERFLOW=100
export DB_POOL_RECYCLE=300
export DB_POOL_TIMEOUT=30

echo "✅ Environment variables configured"

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "📦 Installing dependencies..."
    pip install --upgrade pip
    pip install gunicorn[gthread] psycopg2-binary redis werkzeug flask flask-sqlalchemy flask-login flask-wtf flask-limiter
fi

# Database optimization
echo "🔧 Optimizing database..."
python3 -c "
from app_clean import db, app
with app.app_context():
    # Create indexes if not exist
    db.session.execute('CREATE INDEX IF NOT EXISTS idx_bag_qr_type ON bag(qr_id, type);')
    db.session.execute('CREATE INDEX IF NOT EXISTS idx_scan_timestamp_user ON scan(timestamp DESC, user_id);')
    db.session.execute('CREATE INDEX IF NOT EXISTS idx_bill_status_created ON bill(status, created_at DESC);')
    db.session.commit()
    print('✅ Database indexes created')
"

# Kill any existing gunicorn processes
echo "🔄 Stopping existing processes..."
pkill -f gunicorn || true

# Start gunicorn with production configuration
echo "🚀 Starting Gunicorn with production configuration..."
gunicorn -c gunicorn_config.py main:app --daemon \
    --log-file=/var/log/tracetrack.log \
    --access-logfile=/var/log/tracetrack-access.log \
    --error-logfile=/var/log/tracetrack-error.log

# Wait for startup
sleep 3

# Check if running
if pgrep -f gunicorn > /dev/null; then
    echo "✅ TraceTrack is running in production mode!"
    echo ""
    echo "📊 Configuration:"
    echo "  - Workers: $(pgrep -f gunicorn | wc -l) processes"
    echo "  - Port: 5000"
    echo "  - Mode: Production"
    echo ""
    echo "🔍 Health check: curl http://localhost:5000/health"
    echo "📈 Monitoring logs: tail -f /var/log/tracetrack.log"
else
    echo "❌ Failed to start TraceTrack"
    exit 1
fi

echo "=========================================="
echo "✨ Deployment complete!"