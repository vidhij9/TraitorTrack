#!/usr/bin/env python3
"""
Optimized startup script for TraceTrack
Configures and starts the application with multiple workers for high concurrency
"""

import os
import sys
import multiprocessing

# Determine optimal worker count
cpu_count = multiprocessing.cpu_count()
workers = max(4, cpu_count * 2)  # At least 4 workers

# Build gunicorn command with optimizations
cmd = [
    "gunicorn",
    "--workers", str(workers),
    "--worker-class", "sync",  # Sync workers are best for CPU-bound tasks
    "--worker-connections", "1000",
    "--max-requests", "1000",  # Restart workers after 1000 requests to prevent memory leaks
    "--max-requests-jitter", "50",
    "--bind", "0.0.0.0:5000",
    "--timeout", "120",
    "--keep-alive", "5",
    "--preload",  # Preload app for faster worker startup
    "--log-level", "info",
    "--access-logfile", "-",
    "--error-logfile", "-",
    "main:app"
]

print(f"Starting TraceTrack with {workers} workers for optimal performance...")
print(f"Command: {' '.join(cmd)}")

# Execute gunicorn
os.execvp("gunicorn", cmd)