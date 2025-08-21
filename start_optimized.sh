#!/bin/bash
# Optimized startup script for TraceTrack

echo "Starting TraceTrack with performance optimizations..."

# Set environment variables for optimization
export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=1
export FLASK_ENV=production

# Start with optimized Gunicorn configuration
echo "Starting optimized Gunicorn server..."
gunicorn --config gunicorn_optimized.py main:app
