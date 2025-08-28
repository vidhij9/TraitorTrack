#!/bin/bash
# Optimized startup script for 20+ concurrent scanning users

echo "Starting TraceTrack optimized for 20+ concurrent scanning users..."
echo "Configuration: 8 workers × 4 threads = 32 concurrent handlers"

# Set environment variables for optimization
export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=1
export FLASK_ENV=production

# Start with concurrent scan optimized configuration
echo "Starting Gunicorn with concurrent scanning optimization..."
gunicorn --config gunicorn_concurrent_scan.py main:app
