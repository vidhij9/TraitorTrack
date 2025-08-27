#!/usr/bin/env python3
"""Ultra-Performance Gunicorn Configuration"""

# Server configuration
bind = "0.0.0.0:5000"
workers = 16  # Increased for high concurrency
worker_class = "gevent"
worker_connections = 5000  # Increased for ultra-scale
threads = 8  # Increased threads per worker

# Connection handling
backlog = 4096  # Increased backlog
keepalive = 10
timeout = 120  # Increased timeout for complex operations
graceful_timeout = 60

# Performance tuning
max_requests = 50000  # Increased for stability
max_requests_jitter = 5000
preload_app = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'tracetrack-ultra-performance'

# Security
limit_request_line = 8192
limit_request_fields = 200
limit_request_field_size = 16384

# Enhanced features
enable_stdio_inheritance = True
capture_output = True
reload = False
daemon = False
pidfile = '/tmp/tracetrack-ultra.pid'
user = 'www-data'
group = 'www-data'
tmp_upload_dir = '/tmp/tracetrack-uploads'
check_config = True
