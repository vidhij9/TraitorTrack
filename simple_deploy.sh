#!/bin/bash
# Simple deployment script - no package installation
# Replit handles all packages from pyproject.toml automatically

echo "Starting TraceTrack..."

# Just start Gunicorn directly - no checks, no installs
gunicorn --bind 0.0.0.0:5000 --workers 4 --worker-class gevent --worker-connections 1000 --timeout 120 --preload main:app