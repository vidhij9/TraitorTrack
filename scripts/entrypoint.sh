#!/bin/bash

# TraceTrack Production Entrypoint
# Ensures static assets are properly copied to shared volume before starting app

set -e

echo "🚀 Starting TraceTrack..."

# Handle static assets if shared volume is mounted
if [ -d "/shared/static" ]; then
    echo "📁 Setting up static assets in shared volume..."
    
    # Ensure proper ownership and permissions
    chown -R 1000:1000 /shared/static
    chmod -R 755 /shared/static
    
    # Sync static assets (removes stale files)
    if command -v rsync >/dev/null 2>&1; then
        rsync -a --delete /app/static/ /shared/static/
    else
        # Fallback to cp if rsync not available
        rm -rf /shared/static/*
        cp -r /app/static/* /shared/static/
    fi
    
    echo "✅ Static assets synchronized to shared volume"
fi

# Drop privileges and start the application
echo "🌐 Starting gunicorn server as user app..."
if [ "$(id -u)" = "0" ]; then
    # Running as root, drop to app user
    exec gosu app "$@"
else
    # Already running as app user
    exec "$@"
fi